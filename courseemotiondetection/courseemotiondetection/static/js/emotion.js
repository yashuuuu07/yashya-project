const video = document.getElementById('webcam');
const statusDiv = document.getElementById('status');
const emotionSpan = document.getElementById('currentEmotion');
const engagementSpan = document.getElementById('engagementScore');
const toggleBtn = document.getElementById('toggleTracking');

let isTracking = true;
let modelsLoaded = false;

// Load face-api models from CDN (hosted on GitHub or similar)
// Use weights compatible with version 0.22.2
const MODEL_URL = 'https://justadudewhohacks.github.io/face-api.js/models';

async function setup() {
    // Wait up to 2 seconds for faceapi to become available
    let retryCount = 0;
    while (typeof faceapi === 'undefined' && retryCount < 10) {
        console.log("Waiting for faceapi...");
        await new Promise(resolve => setTimeout(resolve, 200));
        retryCount++;
    }

    if (typeof faceapi === 'undefined') {
        statusDiv.innerText = "Error: Face-API script failed to load after retries.";
        console.error("Face-API is undefined.");
        return;
    }

    try {
        statusDiv.innerText = "Loading AI models...";
        // Official face-api.js 0.22.2 uses these method names
        await faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL);
        await faceapi.nets.faceExpressionNet.loadFromUri(MODEL_URL);

        modelsLoaded = true;
        statusDiv.innerText = "Models loaded. Starting camera...";
        startVideo();
    } catch (err) {
        statusDiv.innerText = "Error loading models: " + err.message;
        console.error("Model loading error:", err);
        // Try starting video anyway to see if camera works
        startVideo();
    }
}

function startVideo() {
    navigator.mediaDevices.getUserMedia({ video: {} })
        .then(stream => {
            video.srcObject = stream;
            statusDiv.innerText = "Tracking Active";
            video.addEventListener('play', () => {
                detectEmotions();
            });
        })
        .catch(err => {
            statusDiv.innerText = "Webcam access denied.";
            console.error(err);
        });
}

async function detectEmotions() {
    if (!isTracking || !modelsLoaded) return;

    const detections = await faceapi.detectSingleFace(video, new faceapi.TinyFaceDetectorOptions())
        .withFaceExpressions();

    if (detections) {
        const expressions = detections.expressions;
        // Get the emotion with highest probability
        const bestEmotion = Object.keys(expressions).reduce((a, b) => expressions[a] > expressions[b] ? a : b);
        const score = expressions[bestEmotion];

        emotionSpan.innerText = bestEmotion;
        engagementSpan.innerText = Math.round(score * 100) + "%";

        // Log to backend every 3 seconds (approx)
        if (Math.random() > 0.7) { // Simple throttled logging
            logEmotion(bestEmotion, score);
        }
    }

    if (isTracking) {
        requestAnimationFrame(detectEmotions);
    }
}

async function logEmotion(emotion, score) {
    try {
        await fetch('/api/log_emotion', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                course_id: COURSE_ID,
                emotion: emotion,
                score: score,
                timestamp: document.getElementById('courseVideo').contentWindow?.postMessage ? 'video-id-sync' : 0 // Placeholder for sync
            })
        });
    } catch (err) {
        console.error("Failed to log emotion:", err);
    }
}

toggleBtn.addEventListener('click', () => {
    isTracking = !isTracking;
    toggleBtn.innerText = isTracking ? "Pause Tracking" : "Resume Tracking";
    statusDiv.innerText = isTracking ? "Tracking Active" : "Tracking Paused";
    if (isTracking) detectEmotions();
});

// Initialize
setup();
