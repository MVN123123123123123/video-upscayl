/**
 * Video-Upscayl Interactive Comparison Player
 * Dual-video synchronized playback, interactive split-slider, 4x magnifier loupe, and model switching.
 */

(function () {
  'use strict';

  // DOM Elements
  const videoOrig = document.getElementById('video-original');
  const videoUp = document.getElementById('video-upscaled');
  const upscaledSource = document.getElementById('upscaled-source');
  const topContainer = document.getElementById('video-top-container');
  const sliderHandle = document.getElementById('slider-handle');
  const viewportWrapper = document.getElementById('viewport-wrapper');
  const playerContainer = document.getElementById('player-container');
  
  const badgeRightText = document.getElementById('badge-right-text');
  const badgeLeft = document.getElementById('badge-left');
  const badgeRight = document.getElementById('badge-right');
  
  const timeDisplay = document.getElementById('time-display');
  const frameDisplay = document.getElementById('frame-display');
  const scrubberContainer = document.getElementById('scrubber-container');
  const scrubberProgress = document.getElementById('scrubber-progress');
  const scrubberThumb = document.getElementById('scrubber-thumb');
  
  const btnPlayPause = document.getElementById('btn-play-pause');
  const playIcon = document.getElementById('play-icon');
  const playLabel = document.getElementById('play-label');
  const btnReplay = document.getElementById('btn-replay');
  const btnMute = document.getElementById('btn-mute');
  const muteIcon = document.getElementById('mute-icon');
  const btnFullscreen = document.getElementById('btn-fullscreen');
  
  const pillSplitVal = document.getElementById('pill-split-val');
  
  // Loupe elements
  const loupeLens = document.getElementById('loupe-lens');
  const loupeCanvas = document.getElementById('loupe-canvas');
  const loupeCtx = loupeCanvas.getContext('2d');
  
  // State
  let currentMode = 'split'; // 'split' | 'side-by-side' | 'loupe' | 'toggle'
  let currentModel = '3x';
  let splitPosition = 50; // percentage (0 - 100)
  let isDraggingSlider = false;
  let isScrubbing = false;
  let isToggledUpscaled = true;
  
  const MODELS = {
    '3x': {
      name: 'Real-CUGAN 3x (Pro)',
      res: '3072×1728',
      src: 'videos/demo_upscaled_3x.mp4'
    },
    '2x': {
      name: 'Real-ESRGAN 2x (Anime)',
      res: '2048×1152',
      src: 'videos/demo_upscaled_2x.mp4'
    }
  };

  // --- Slider Split Logic ---
  function updateSplitPosition(pct) {
    pct = Math.max(0, Math.min(100, pct));
    splitPosition = pct;
    
    if (currentMode === 'split') {
      topContainer.style.clipPath = `polygon(0 0, ${pct}% 0, ${pct}% 100%, 0 100%)`;
      sliderHandle.style.left = `${pct}%`;
      sliderHandle.style.display = 'flex';
      pillSplitVal.textContent = `${Math.round(pct)}%`;
    }
  }

  function handleSliderMove(clientX) {
    const rect = playerContainer.getBoundingClientRect();
    if (rect.width <= 0) return;
    const x = clientX - rect.left;
    const pct = (x / rect.width) * 100;
    updateSplitPosition(pct);
  }

  sliderHandle.addEventListener('pointerdown', (e) => {
    isDraggingSlider = true;
    sliderHandle.setPointerCapture(e.pointerId);
    e.preventDefault();
  });

  sliderHandle.addEventListener('pointermove', (e) => {
    if (isDraggingSlider) {
      handleSliderMove(e.clientX);
    }
  });

  sliderHandle.addEventListener('pointerup', (e) => {
    isDraggingSlider = false;
    try { sliderHandle.releasePointerCapture(e.pointerId); } catch (_) {}
  });

  sliderHandle.addEventListener('pointercancel', (e) => {
    isDraggingSlider = false;
  });

  // Clicking anywhere on viewport in split mode moves slider smoothly
  playerContainer.addEventListener('click', (e) => {
    if (currentMode === 'split' && !isDraggingSlider) {
      handleSliderMove(e.clientX);
    }
  });

  // --- View Mode Selector ---
  const modeButtons = document.querySelectorAll('#mode-selector .segmented-btn');
  modeButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      modeButtons.forEach(b => {
        b.classList.remove('active');
        b.setAttribute('aria-selected', 'false');
      });
      btn.classList.add('active');
      btn.setAttribute('aria-selected', 'true');
      setMode(btn.dataset.mode);
    });
  });

  function setMode(mode) {
    currentMode = mode;
    viewportWrapper.classList.remove('mode-side-by-side');
    loupeLens.style.display = 'none';
    sliderHandle.style.display = 'none';
    
    // Reset video layer styling
    topContainer.style.width = '100%';
    videoOrig.style.width = '100%';
    videoOrig.style.opacity = '1';
    videoUp.style.opacity = '1';

    if (mode === 'split') {
      sliderHandle.style.display = 'flex';
      updateSplitPosition(splitPosition);
      badgeLeft.style.display = 'flex';
      badgeRight.style.display = 'flex';
      badgeLeft.style.left = '24px';
      badgeRight.style.right = '24px';
    } else if (mode === 'side-by-side') {
      viewportWrapper.classList.add('mode-side-by-side');
      topContainer.style.clipPath = 'none';
      badgeLeft.style.display = 'flex';
      badgeRight.style.display = 'flex';
      badgeLeft.style.left = '16px';
      badgeRight.style.right = '16px';
    } else if (mode === 'loupe') {
      // Top layer hidden; loupe reveals upscaled layer zoomed in
      topContainer.style.clipPath = 'polygon(0 0, 0 0, 0 100%, 0 100%)';
      loupeLens.style.display = 'block';
      badgeLeft.style.display = 'flex';
      badgeRight.style.display = 'flex';
      badgeRight.querySelector('span:last-child').textContent = 'Loupe: ' + MODELS[currentModel].name;
    } else if (mode === 'toggle') {
      isToggledUpscaled = true;
      applyToggleState();
    }
  }

  function applyToggleState() {
    if (isToggledUpscaled) {
      topContainer.style.clipPath = 'polygon(0 0, 100% 0, 100% 100%, 0 100%)';
      badgeLeft.style.display = 'none';
      badgeRight.style.display = 'flex';
    } else {
      topContainer.style.clipPath = 'polygon(0 0, 0 0, 0 100%, 0 100%)';
      badgeLeft.style.display = 'flex';
      badgeRight.style.display = 'none';
    }
  }

  // In Toggle mode, click or press 'T' to switch
  playerContainer.addEventListener('mousedown', (e) => {
    if (currentMode === 'toggle') {
      isToggledUpscaled = !isToggledUpscaled;
      applyToggleState();
    }
  });

  // --- Loupe Magnifier Logic ---
  playerContainer.addEventListener('mousemove', (e) => {
    if (currentMode !== 'loupe') return;
    const rect = playerContainer.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const lensSize = 220;
    const halfLens = lensSize / 2;

    loupeLens.style.left = `${mouseX - halfLens}px`;
    loupeLens.style.top = `${mouseY - halfLens}px`;

    // Render 4x magnified crop of upscaled video on loupe canvas
    if (loupeCanvas.width !== lensSize) {
      loupeCanvas.width = lensSize;
      loupeCanvas.height = lensSize;
    }

    const zoomFactor = 4;
    // Normalized coordinates inside video
    const normX = mouseX / rect.width;
    const normY = mouseY / rect.height;

    const sw = (videoUp.videoWidth || 1920) / zoomFactor;
    const sh = (videoUp.videoHeight || 1080) / zoomFactor;
    const sx = Math.max(0, Math.min((videoUp.videoWidth || 1920) - sw, normX * (videoUp.videoWidth || 1920) - sw / 2));
    const sy = Math.max(0, Math.min((videoUp.videoHeight || 1080) - sh, normY * (videoUp.videoHeight || 1080) - sh / 2));

    try {
      loupeCtx.drawImage(videoUp, sx, sy, sw, sh, 0, 0, lensSize, lensSize);
    } catch (_) {}
  });

  // --- Model Switcher ---
  const modelButtons = document.querySelectorAll('#model-selector .segmented-btn');
  modelButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      modelButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      switchModel(btn.dataset.model);
    });
  });

  function switchModel(modelKey) {
    if (!MODELS[modelKey]) return;
    currentModel = modelKey;
    const info = MODELS[modelKey];
    
    badgeRightText.textContent = `${info.name} (${info.res})`;
    
    const wasPlaying = !videoOrig.paused;
    const currTime = videoOrig.currentTime;
    
    upscaledSource.src = info.src;
    videoUp.load();
    videoUp.currentTime = currTime;
    
    if (wasPlaying) {
      videoUp.play().catch(() => {});
      videoOrig.play().catch(() => {});
    }
  }

  // --- Video Synchronization Loop ---
  function syncLoop() {
    if (!videoOrig.paused && !videoUp.paused) {
      const diff = Math.abs(videoOrig.currentTime - videoUp.currentTime);
      if (diff > 0.05) {
        videoUp.currentTime = videoOrig.currentTime;
      }
    }

    // Update time & scrubber
    if (!isScrubbing && videoOrig.duration) {
      const cur = videoOrig.currentTime;
      const dur = videoOrig.duration;
      const pct = (cur / dur) * 100;
      scrubberProgress.style.width = `${pct}%`;
      scrubberThumb.style.left = `${pct}%`;

      timeDisplay.textContent = `${formatTime(cur)} / ${formatTime(dur)}`;
      const frameNum = Math.floor(cur * 30);
      const totalFrames = Math.floor(dur * 30);
      frameDisplay.textContent = `Frame ${frameNum} / ${totalFrames}`;
    }

    // Continuously render loupe if active and playing
    if (currentMode === 'loupe' && !videoOrig.paused) {
      // triggers redraw
    }

    requestAnimationFrame(syncLoop);
  }
  requestAnimationFrame(syncLoop);

  function formatTime(secs) {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }

  // --- Playback Controls ---
  function togglePlay() {
    if (videoOrig.paused) {
      videoOrig.play();
      videoUp.play();
      playIcon.textContent = '⏸';
      playLabel.textContent = 'Pause';
      btnPlayPause.classList.remove('btn-play');
    } else {
      videoOrig.pause();
      videoUp.pause();
      playIcon.textContent = '▶';
      playLabel.textContent = 'Play';
      btnPlayPause.classList.add('btn-play');
    }
  }

  btnPlayPause.addEventListener('click', togglePlay);

  btnReplay.addEventListener('click', () => {
    videoOrig.currentTime = 0;
    videoUp.currentTime = 0;
    if (videoOrig.paused) {
      togglePlay();
    }
  });

  // Mute / Unmute
  btnMute.addEventListener('click', () => {
    videoOrig.muted = !videoOrig.muted;
    videoUp.muted = true; // keep upscaled muted to prevent echo
    muteIcon.textContent = videoOrig.muted ? '🔇' : '🔊';
  });

  // Speed selectors
  const speedButtons = document.querySelectorAll('.action-btn-group [data-speed]');
  speedButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      speedButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const rate = parseFloat(btn.dataset.speed);
      videoOrig.playbackRate = rate;
      videoUp.playbackRate = rate;
    });
  });

  // Scrubber scrubbing
  function handleScrubber(clientX) {
    const rect = scrubberContainer.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    if (videoOrig.duration) {
      videoOrig.currentTime = ratio * videoOrig.duration;
      videoUp.currentTime = ratio * videoOrig.duration;
    }
  }

  scrubberContainer.addEventListener('pointerdown', (e) => {
    isScrubbing = true;
    scrubberContainer.setPointerCapture(e.pointerId);
    handleScrubber(e.clientX);
    e.preventDefault();
  });

  scrubberContainer.addEventListener('pointermove', (e) => {
    if (isScrubbing) {
      handleScrubber(e.clientX);
    }
  });

  scrubberContainer.addEventListener('pointerup', (e) => {
    isScrubbing = false;
    try { scrubberContainer.releasePointerCapture(e.pointerId); } catch (_) {}
  });

  // Fullscreen
  btnFullscreen.addEventListener('click', () => {
    if (!document.fullscreenElement) {
      viewportWrapper.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  });

  // Keyboard Shortcuts
  window.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    
    if (e.code === 'Space') {
      e.preventDefault();
      togglePlay();
    } else if (e.code === 'ArrowLeft') {
      e.preventDefault();
      videoOrig.currentTime = Math.max(0, videoOrig.currentTime - 1);
      videoUp.currentTime = videoOrig.currentTime;
    } else if (e.code === 'ArrowRight') {
      e.preventDefault();
      videoOrig.currentTime = Math.min(videoOrig.duration, videoOrig.currentTime + 1);
      videoUp.currentTime = videoOrig.currentTime;
    } else if (e.code === 'KeyM') {
      btnMute.click();
    } else if (e.code === 'KeyT') {
      if (currentMode === 'toggle') {
        isToggledUpscaled = !isToggledUpscaled;
        applyToggleState();
      }
    }
  });

  // Initialize
  updateSplitPosition(50);
})();
