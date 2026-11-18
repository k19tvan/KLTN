/**
 * REC-8K Video Transformation Studio - Frontend Client
 * Handles dataset browsing, Canvas point visualizer, LLM scripting,
 * and drag-and-drop persistent video upload.
 */

(() => {
  "use strict";

  // Application State
  const state = {
    samples: [],
    selectedSample: null,
    categories: [],
    stats: null,
    currentPage: 1,
    pageSize: 20,
    totalPages: 1,
    selectedCategory: "all",
    selectedStatus: "all",
    searchQuery: "",
    showPoints: true,
    loadedImage: null,
  };

  // DOM Elements
  const el = {
    statTotalSamples: document.getElementById("statTotalSamples"),
    statScriptedLabel: document.getElementById("statScriptedLabel"),
    statScriptedFill: document.getElementById("statScriptedFill"),
    statVideoLabel: document.getElementById("statVideoLabel"),
    statVideoFill: document.getElementById("statVideoFill"),
    searchInput: document.getElementById("searchInput"),
    categorySelect: document.getElementById("categorySelect"),
    statusSelect: document.getElementById("statusSelect"),
    sampleList: document.getElementById("sampleList"),
    btnPrevPage: document.getElementById("btnPrevPage"),
    btnNextPage: document.getElementById("btnNextPage"),
    pageInfo: document.getElementById("pageInfo"),
    sampleDetailTitle: document.getElementById("sampleDetailTitle"),
    sampleDetailSubtitle: document.getElementById("sampleDetailSubtitle"),
    sampleMetaPills: document.getElementById("sampleMetaPills"),
    workspaceContent: document.getElementById("workspaceContent"),
    btnOpenRawImage: document.getElementById("btnOpenRawImage"),
    btnTogglePoints: document.getElementById("btnTogglePoints"),
    toggleDotsIcon: document.getElementById("toggleDotsIcon"),
    toggleDotsText: document.getElementById("toggleDotsText"),
    pointsCountBadge: document.getElementById("pointsCountBadge"),
    btnTogglePointsBottom: document.getElementById("btnTogglePointsBottom"),
    pointCanvas: document.getElementById("pointCanvas"),
    togglePointsCheckbox: document.getElementById("togglePointsCheckbox"),
    pointsCountLabel: document.getElementById("pointsCountLabel"),
    imageDimLabel: document.getElementById("imageDimLabel"),
    pointsCoordinatesBox: document.getElementById("pointsCoordinatesBox"),
    inputDisappear: document.getElementById("inputDisappear"),
    inputAppear: document.getElementById("inputAppear"),
    computedFinalCount: document.getElementById("computedFinalCount"),
    btnGenerateScript: document.getElementById("btnGenerateScript"),
    btnScriptText: document.getElementById("btnScriptText"),
    scriptTextarea: document.getElementById("scriptTextarea"),
    btnCopyPrompt: document.getElementById("btnCopyPrompt"),
    btnSaveScript: document.getElementById("btnSaveScript"),
    videoDropzone: document.getElementById("videoDropzone"),
    videoFileInput: document.getElementById("videoFileInput"),
    videoPlayerSection: document.getElementById("videoPlayerSection"),
    sampleVideoPlayer: document.getElementById("sampleVideoPlayer"),
    videoFilenameLabel: document.getElementById("videoFilenameLabel"),
    btnReplaceVideo: document.getElementById("btnReplaceVideo"),
    btnRemoveVideo: document.getElementById("btnRemoveVideo"),
    toastNotification: document.getElementById("toastNotification"),
  };

  // Toast Notification Helper
  function showToast(message, durationMs = 3000) {
    el.toastNotification.textContent = message;
    el.toastNotification.style.display = "block";
    clearTimeout(showToast._timer);
    showToast._timer = setTimeout(() => {
      el.toastNotification.style.display = "none";
    }, durationMs);
  }

  // API Client Methods
  async function apiFetchStats() {
    try {
      const res = await fetch("/api/stats");
      if (!res.ok) throw new Error("Failed to load project stats");
      state.stats = await res.json();
      renderStats();
    } catch (err) {
      console.error(err);
    }
  }

  async function apiFetchCategories() {
    try {
      const res = await fetch("/api/categories");
      if (!res.ok) throw new Error("Failed to load categories");
      state.categories = await res.json();
      renderCategoryDropdown();
    } catch (err) {
      console.error(err);
    }
  }

  async function apiFetchSamples() {
    const params = new URLSearchParams({
      page: state.currentPage,
      page_size: state.pageSize,
    });
    if (state.selectedCategory !== "all") params.append("category", state.selectedCategory);
    if (state.selectedStatus !== "all") params.append("status", state.selectedStatus);
    if (state.searchQuery.trim()) params.append("search", state.searchQuery.trim());

    try {
      const res = await fetch(`/api/samples?${params.toString()}`);
      if (!res.ok) throw new Error("Failed to fetch samples");
      const data = await res.json();
      state.samples = data.samples;
      state.totalPages = data.total_pages;
      state.currentPage = data.page;
      renderSampleList();
      renderPagination(data.total_count);
    } catch (err) {
      console.error(err);
      showToast("Error loading samples");
    }
  }

  async function apiSelectSample(sampleId) {
    try {
      const res = await fetch(`/api/samples/${sampleId}`);
      if (!res.ok) throw new Error("Failed to fetch sample details");
      const sample = await res.json();
      state.selectedSample = sample;
      renderSampleDetail(sample);

      // Highlight active item in sidebar
      document.querySelectorAll(".sample-card").forEach((card) => {
        card.classList.toggle("active", card.dataset.id === sampleId);
      });
    } catch (err) {
      console.error(err);
      showToast("Error loading sample details");
    }
  }

  async function apiGenerateScript() {
    if (!state.selectedSample) return;

    const disappearCnt = parseInt(el.inputDisappear.value, 10) || 0;
    const appearCnt = parseInt(el.inputAppear.value, 10) || 0;

    el.btnGenerateScript.disabled = true;
    el.btnScriptText.textContent = "⏳ Generating 6s Script with LLM...";

    try {
      const res = await fetch(`/api/samples/${state.selectedSample.id}/script`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          disappear_cnt: disappearCnt,
          appear_cnt: appearCnt,
        }),
      });

      if (!res.ok) throw new Error("Failed to generate script");
      const data = await res.json();

      state.selectedSample.script = data.script;
      state.selectedSample.script_params.disappear_cnt = disappearCnt;
      state.selectedSample.script_params.appear_cnt = appearCnt;
      if (state.selectedSample.status === "pending") {
        state.selectedSample.status = "scripted";
      }

      el.scriptTextarea.value = data.script;
      updateSamplePills(state.selectedSample);
      showToast("✅ 6-second video script generated!");
      apiFetchStats();
      apiFetchSamples(); // update badge in list
    } catch (err) {
      console.error(err);
      showToast("❌ Script generation failed. Check server log.");
    } finally {
      el.btnGenerateScript.disabled = false;
      el.btnScriptText.textContent = "✨ Generate 6-Second Script";
    }
  }

  async function apiSaveScriptEdits() {
    if (!state.selectedSample) return;
    const updatedScript = el.scriptTextarea.value;
    const disappearCnt = parseInt(el.inputDisappear.value, 10) || 0;
    const appearCnt = parseInt(el.inputAppear.value, 10) || 0;

    try {
      const res = await fetch(`/api/samples/${state.selectedSample.id}/script`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          script: updatedScript,
          disappear_cnt: disappearCnt,
          appear_cnt: appearCnt,
        }),
      });
      if (!res.ok) throw new Error("Failed to update script");
      const sample = await res.json();
      state.selectedSample = sample;
      showToast("💾 Script edits saved successfully!");
      apiFetchStats();
    } catch (err) {
      console.error(err);
      showToast("❌ Failed to save script edits.");
    }
  }

  async function apiUploadVideo(file) {
    if (!state.selectedSample) return;

    const formData = new FormData();
    formData.append("file", file);

    showToast("⏳ Uploading & saving video...");

    try {
      const res = await fetch(`/api/samples/${state.selectedSample.id}/video`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Video upload failed");
      }

      const sample = await res.json();
      state.selectedSample = sample;
      renderVideoSection(sample);
      updateSamplePills(sample);
      showToast("🎉 Video successfully saved permanently!");
      apiFetchStats();
      apiFetchSamples();
    } catch (err) {
      console.error(err);
      showToast(`❌ ${err.message}`);
    }
  }

  async function apiDeleteVideo() {
    if (!state.selectedSample) return;
    if (!confirm("Are you sure you want to remove the video for this sample?")) return;

    try {
      const res = await fetch(`/api/samples/${state.selectedSample.id}/video`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to remove video");
      const sample = await res.json();
      state.selectedSample = sample;
      renderVideoSection(sample);
      updateSamplePills(sample);
      showToast("🗑️ Video removed from sample.");
      apiFetchStats();
      apiFetchSamples();
    } catch (err) {
      console.error(err);
      showToast("❌ Error deleting video.");
    }
  }

  // UI Renderers
  function renderStats() {
    if (!state.stats) return;
    const total = state.stats.total_samples || 1;
    const scripted = state.stats.scripted_count || 0;
    const video = state.stats.video_uploaded_count || 0;

    const scriptedPct = Math.round((scripted / total) * 100);
    const videoPct = Math.round((video / total) * 100);

    el.statTotalSamples.textContent = state.stats.total_samples;
    el.statScriptedLabel.textContent = `Scripted: ${scripted}/${total} (${scriptedPct}%)`;
    el.statScriptedFill.style.width = `${scriptedPct}%`;

    el.statVideoLabel.textContent = `Videos: ${video}/${total} (${videoPct}%)`;
    el.statVideoFill.style.width = `${videoPct}%`;
  }

  function renderCategoryDropdown() {
    const currentVal = el.categorySelect.value;
    el.categorySelect.innerHTML = `<option value="all">All Categories (${state.stats?.total_samples || ""})</option>`;
    state.categories.forEach((cat) => {
      const opt = document.createElement("option");
      opt.value = cat.name;
      opt.textContent = `${cat.name} (${cat.total_samples})`;
      el.categorySelect.appendChild(opt);
    });
    el.categorySelect.value = currentVal;
  }

  function renderSampleList() {
    el.sampleList.innerHTML = "";

    if (state.samples.length === 0) {
      el.sampleList.innerHTML = `
        <div style="text-align: center; color: var(--text-muted); padding: 40px 10px; font-size: 0.88rem;">
          No samples found matching criteria.
        </div>
      `;
      return;
    }

    state.samples.forEach((sample) => {
      const card = document.createElement("div");
      card.className = "sample-card";
      card.dataset.id = sample.id;
      if (state.selectedSample && state.selectedSample.id === sample.id) {
        card.classList.add("active");
      }

      const imageUrl = `/media/images/${sample.image_filename}`;

      let statusBadgeClass = "badge-pending";
      let statusText = "Pending";
      if (sample.status === "video_uploaded") {
        statusBadgeClass = "badge-video";
        statusText = "Video Ready";
      } else if (sample.status === "scripted") {
        statusBadgeClass = "badge-scripted";
        statusText = "Scripted";
      }

      card.innerHTML = `
        <img class="sample-thumb" src="${imageUrl}" loading="lazy" alt="${sample.description}" />
        <div class="sample-info">
          <div class="sample-desc" title="${sample.description}">${sample.description}</div>
          <div class="sample-meta">
            <span class="badge badge-count">N = ${sample.counting_answer}</span>
            <span class="badge ${statusBadgeClass}">${statusText}</span>
          </div>
        </div>
      `;

      card.addEventListener("click", () => apiSelectSample(sample.id));
      el.sampleList.appendChild(card);
    });
  }

  function renderPagination(totalCount) {
    el.pageInfo.textContent = `Page ${state.currentPage} of ${state.totalPages} (${totalCount} total)`;
    el.btnPrevPage.disabled = state.currentPage <= 1;
    el.btnNextPage.disabled = state.currentPage >= state.totalPages;
  }

  function updateSamplePills(sample) {
    let statusBadgeClass = "badge-pending";
    let statusText = "Pending Script & Video";
    if (sample.status === "video_uploaded") {
      statusBadgeClass = "badge-video";
      statusText = "✅ Video Ready";
    } else if (sample.status === "scripted") {
      statusBadgeClass = "badge-scripted";
      statusText = "📝 Scripted";
    }

    el.sampleMetaPills.innerHTML = `
      <span class="badge badge-count" style="font-size: 0.82rem; padding: 4px 10px;">Count: ${sample.counting_answer}</span>
      <span class="badge ${statusBadgeClass}" style="font-size: 0.82rem; padding: 4px 10px;">${statusText}</span>
    `;
  }

  function updateTogglePointsButtonUI() {
    const isShowing = state.showPoints;
    const count = state.selectedSample?.points?.length || 0;

    if (el.btnTogglePoints) {
      el.btnTogglePoints.classList.toggle("active", isShowing);
      el.btnTogglePoints.classList.toggle("inactive", !isShowing);
      if (el.toggleDotsIcon) el.toggleDotsIcon.textContent = isShowing ? "🔴" : "⚪";
      if (el.toggleDotsText) el.toggleDotsText.textContent = isShowing ? "Hide Red Dots" : "Show Red Dots";
      if (el.pointsCountBadge) el.pointsCountBadge.textContent = count;
    }

    if (el.btnTogglePointsBottom) {
      el.btnTogglePointsBottom.classList.toggle("active", isShowing);
      el.btnTogglePointsBottom.innerHTML = isShowing
        ? "<span>🔴 Hide Red Dots</span>"
        : "<span>⚪ Show Red Dots</span>";
    }

    if (el.pointsCountLabel) el.pointsCountLabel.textContent = count;
  }

  function renderSampleDetail(sample) {
    el.workspaceContent.style.display = "grid";
    el.sampleDetailTitle.innerHTML = `
      <span>${sample.description}</span>
      <span class="badge" style="background-color: var(--accent-primary); color: #fff;">${sample.category_type}</span>
    `;
    el.sampleDetailSubtitle.textContent = `Image: ${sample.image_filename} | Target Class: "${sample.target_class}" | Attribute: "${sample.attribute || 'none'}"`;

    updateSamplePills(sample);

    // Direct Image Link
    const imgUrl = `/media/images/${sample.image_filename}`;
    el.btnOpenRawImage.href = imgUrl;

    // Load Image & Draw Canvas
    updateTogglePointsButtonUI();
    loadImageAndRenderCanvas(imgUrl, sample.points);

    // Render Coordinates Summary
    renderPointsCoordinates(sample.points);

    // Step 1: Script Dynamics
    const disappear = sample.script_params?.disappear_cnt ?? 1;
    const appear = sample.script_params?.appear_cnt ?? 0;
    el.inputDisappear.value = disappear;
    el.inputAppear.value = appear;
    recalculateFinalCount(sample.counting_answer, disappear, appear);

    el.scriptTextarea.value = sample.script || "";

    // Step 2: Video Player
    renderVideoSection(sample);
  }

  function renderPointsCoordinates(points) {
    if (!points || points.length === 0) {
      el.pointsCoordinatesBox.textContent = "No coordinate points recorded.";
      return;
    }
    const lines = points.map((p, idx) => `Point #${idx + 1}: x = ${p[0].toFixed(1)}, y = ${p[1].toFixed(1)}`);
    el.pointsCoordinatesBox.innerHTML = lines.join("<br/>");
  }

  function loadImageAndRenderCanvas(imgUrl, points) {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.src = imgUrl;
    img.onload = () => {
      state.loadedImage = img;
      el.imageDimLabel.textContent = `${img.naturalWidth} × ${img.naturalHeight}px`;
      drawCanvas(img, points, state.showPoints);
    };
    img.onerror = () => {
      console.error("Failed to load image at", imgUrl);
      el.imageDimLabel.textContent = "Failed to load image";
    };
  }

  function drawCanvas(img, points, showPoints) {
    const canvas = el.pointCanvas;
    const ctx = canvas.getContext("2d");

    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;

    // Draw base image
    ctx.drawImage(img, 0, 0);

    if (!showPoints || !points || points.length === 0) return;

    // Calculate dynamic point radius proportional to image scale
    const maxDim = Math.max(canvas.width, canvas.height);
    const baseRadius = Math.max(10, Math.min(Math.round(maxDim * 0.016), 40));
    const strokeWidth = Math.max(2, Math.round(baseRadius * 0.18));
    const fontSize = Math.max(11, Math.round(baseRadius * 1.05));

    points.forEach((point, index) => {
      const [x, y] = point;

      // Outer glow/stroke
      ctx.beginPath();
      ctx.arc(x, y, baseRadius + 3, 0, 2 * Math.PI);
      ctx.fillStyle = "rgba(0, 0, 0, 0.6)";
      ctx.fill();

      // Main vibrant point circle
      ctx.beginPath();
      ctx.arc(x, y, baseRadius, 0, 2 * Math.PI);
      ctx.fillStyle = "#ef4444"; // Vivid red
      ctx.fill();

      // Inner white boundary
      ctx.lineWidth = strokeWidth;
      ctx.strokeStyle = "#ffffff";
      ctx.stroke();

      // Number label centered
      ctx.font = `bold ${fontSize}px sans-serif`;
      ctx.fillStyle = "#ffffff";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText((index + 1).toString(), x, y);
    });
  }

  function recalculateFinalCount(initialCount, disappear, appear) {
    const finalCount = Math.max(0, initialCount - disappear + appear);
    el.computedFinalCount.textContent = finalCount;
  }

  function renderVideoSection(sample) {
    if (sample.video_filename) {
      el.videoDropzone.style.display = "none";
      el.videoPlayerSection.style.display = "flex";
      el.sampleVideoPlayer.src = `/media/videos/${sample.video_filename}`;
      el.videoFilenameLabel.textContent = `(${sample.video_filename})`;
    } else {
      el.videoPlayerSection.style.display = "none";
      el.videoDropzone.style.display = "flex";
      el.sampleVideoPlayer.src = "";
    }
  }

  // Event Listeners Setup
  function setupEventListeners() {
    // Search input
    let searchTimeout;
    el.searchInput.addEventListener("input", (e) => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        state.searchQuery = e.target.value;
        state.currentPage = 1;
        apiFetchSamples();
      }, 250);
    });

    // Category dropdown
    el.categorySelect.addEventListener("change", (e) => {
      state.selectedCategory = e.target.value;
      state.currentPage = 1;
      apiFetchSamples();
    });

    // Status dropdown
    el.statusSelect.addEventListener("change", (e) => {
      state.selectedStatus = e.target.value;
      state.currentPage = 1;
      apiFetchSamples();
    });

    // Pagination
    el.btnPrevPage.addEventListener("click", () => {
      if (state.currentPage > 1) {
        state.currentPage -= 1;
        apiFetchSamples();
      }
    });

    el.btnNextPage.addEventListener("click", () => {
      if (state.currentPage < state.totalPages) {
        state.currentPage += 1;
        apiFetchSamples();
      }
    });

    // Toggle Points Buttons & Handlers
    function handleTogglePoints() {
      state.showPoints = !state.showPoints;
      updateTogglePointsButtonUI();
      if (state.loadedImage && state.selectedSample) {
        drawCanvas(state.loadedImage, state.selectedSample.points, state.showPoints);
      }
      showToast(state.showPoints ? "🔴 Red dots enabled" : "⚪ Red dots hidden", 1200);
    }

    if (el.btnTogglePoints) {
      el.btnTogglePoints.addEventListener("click", handleTogglePoints);
    }
    if (el.btnTogglePointsBottom) {
      el.btnTogglePointsBottom.addEventListener("click", handleTogglePoints);
    }

    // Dynamic final count inputs
    const handleCountChange = () => {
      if (!state.selectedSample) return;
      const disappear = parseInt(el.inputDisappear.value, 10) || 0;
      const appear = parseInt(el.inputAppear.value, 10) || 0;
      recalculateFinalCount(state.selectedSample.counting_answer, disappear, appear);
    };
    el.inputDisappear.addEventListener("input", handleCountChange);
    el.inputAppear.addEventListener("input", handleCountChange);

    // Generate Script button
    el.btnGenerateScript.addEventListener("click", apiGenerateScript);

    // Save Edits button
    el.btnSaveScript.addEventListener("click", apiSaveScriptEdits);

    // Copy Prompt button
    el.btnCopyPrompt.addEventListener("click", () => {
      const text = el.scriptTextarea.value.trim();
      if (!text) {
        showToast("No script text to copy.");
        return;
      }
      navigator.clipboard.writeText(text).then(
        () => showToast("📋 Video prompt copied to clipboard!"),
        () => showToast("Failed to copy to clipboard")
      );
    });

    // Dropzone interaction & Drag-and-Drop
    el.videoDropzone.addEventListener("click", () => el.videoFileInput.click());

    el.videoFileInput.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (file) apiUploadVideo(file);
    });

    ["dragenter", "dragover"].forEach((eventName) => {
      el.videoDropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        el.videoDropzone.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      el.videoDropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        el.videoDropzone.classList.remove("dragover");
      });
    });

    el.videoDropzone.addEventListener("drop", (e) => {
      const file = e.dataTransfer.files[0];
      if (file) apiUploadVideo(file);
    });

    // Video Player actions
    el.btnReplaceVideo.addEventListener("click", () => el.videoFileInput.click());
    el.btnRemoveVideo.addEventListener("click", apiDeleteVideo);
  }

  // Initialization
  async function init() {
    setupEventListeners();
    await apiFetchStats();
    await apiFetchCategories();
    await apiFetchSamples();

    // Auto-select first sample if available
    if (state.samples.length > 0) {
      apiSelectSample(state.samples[0].id);
    }
  }

  init();
})();
