// ==================== COMMON JS FOR ALL 30 DAYS ====================
// MODULAR VERSION - Load only what you need for each day

// ==================== BLOCK 1: UTILITY FUNCTIONS (ALWAYS NEEDED) ====================

// Global variables
let currentDay = 1;
let currentLevel = 'intermediate';
let activityCompleted = {
    listening: false,
    vocabulary: false,
    grammar: false
};

// Page configuration
let pageConfig = {
    quizAnswers: { q1: '', q2: '' },
    vocabularyWords: [],
    powerWord: 'perspicacious',
    grammarAnswers: {
        q1: { keyword: '', message: '', errorMessage: '' },
        q2: { keyword: '', message: '', errorMessage: '' },
        q3: { keyword: '', message: '', errorMessage: '' },
        q4: { keyword: '', message: '', errorMessage: '' }
    }
};

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function updateChecklistProgress() {
    const checkboxes = ['chk1', 'chk2', 'chk3', 'chk4', 'chk5'];
    let completed = 0;
    for (let i = 0; i < checkboxes.length; i++) {
        if (document.getElementById(checkboxes[i])?.checked) completed++;
    }
    const counter = document.getElementById('progressCounter');
    if (counter) counter.innerText = `${completed}/5 completed`;
    const dayBtn = document.getElementById('dayCompleteBtn');
    if (dayBtn) {
        dayBtn.disabled = (completed !== 5);
        dayBtn.style.opacity = (completed === 5) ? '1' : '0.5';
    }
}

function markActivityComplete(activityId, checklistId) {
    if (activityCompleted[activityId]) return;
    activityCompleted[activityId] = true;
    const checkbox = document.getElementById(checklistId);
    if (checkbox) checkbox.checked = true;
    const btn = document.getElementById(`complete${activityId.charAt(0).toUpperCase() + activityId.slice(1)}Btn`);
    if (btn) {
        btn.classList.add('completed');
        btn.textContent = '✓ Completed';
        btn.disabled = true;
    }
    updateChecklistProgress();
    saveProgress(); // persist to localStorage

    fetch(`/learning/level/${currentLevel}/day/${currentDay}/complete/${activityId}/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken'), 'Content-Type': 'application/json' },
        body: JSON.stringify({ completed: true })
    }).catch(err => console.error('Error saving activity:', err));
}

function completeDay() {
    const btn = document.getElementById('dayCompleteBtn');
    if (!btn || btn.disabled) return;

    btn.innerHTML = '✨ Completing day...';
    btn.disabled = true;

    // Proceed directly to saving and celebration
    fetch(`/learning/level/${currentLevel}/day/${currentDay}/complete/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken'), 'Content-Type': 'application/json' },
        body: JSON.stringify({ completed: true })
    }).then(() => {
        if (typeof confetti === 'function') {
            confetti({ particleCount: 200, spread: 100, origin: { y: 0.6 } });
        } else if (typeof window.confetti === 'function') {
            window.confetti({ particleCount: 200, spread: 100, origin: { y: 0.6 } });
        }

        btn.innerHTML = '✓ Day Completed! 🎉';
        clearDayProgress();

        setTimeout(() => {
            window.location.href = `/learning/level/${currentLevel}/?celebrate=true&completed=${currentDay}`;
        }, 1500);
    }).catch(() => {
        // Even on network error, we treat it as completed locally for the user's flow
        if (typeof confetti === 'function') {
            confetti({ particleCount: 200, spread: 100, origin: { y: 0.6 } });
        } else if (typeof window.confetti === 'function') {
            window.confetti({ particleCount: 200, spread: 100, origin: { y: 0.6 } });
        }

        btn.innerHTML = '✓ Day Completed! 🎉';
        clearDayProgress();

        setTimeout(() => {
            window.location.href = `/learning/level/${currentLevel}/?celebrate=true&completed=${currentDay}`;
        }, 1500);
    });
}

// ==================== BLOCK 2: LISTENING ACTIVITY (OPTIONAL) ====================

function initListeningActivity() {
    const audio = document.getElementById('listeningAudio');
    const listeningTextSection = document.getElementById('listeningTextSection');
    const postAudioContent = document.getElementById('postAudioListeningContent');
    const recordBtn = document.getElementById('listeningRecordBtn');
    const stopBtn = document.getElementById('listeningStopBtn');
    const playbackCard = document.getElementById('listeningPlaybackCard');
    const playbackAudio = document.getElementById('listeningPlayback');
    const comparisonSection = document.getElementById('comparisonSection');
    const yesBtn = document.getElementById('yesComparisonBtn');
    const noBtn = document.getElementById('noComparisonBtn');
    const comparisonFeedback = document.getElementById('comparisonFeedback');
    const checkBtn = document.getElementById('checkListeningWorkBtn');
    const completeListeningBtn = document.getElementById('completeListeningBtn');
    const quizFeedback = document.getElementById('listeningQuizFeedback');

    let mediaRecorder = null;
    let audioChunks = [];
    let isRecording = false;
    let quizCompleted = false;
    let recordingConfirmed = false;
    let q1Correct = false;
    let q2Correct = false;

    if (audio) {
        audio.addEventListener('ended', function () {
            if (listeningTextSection) listeningTextSection.style.display = 'block';
            if (postAudioContent) postAudioContent.style.display = 'block';
        });
    }

    if (recordBtn) {
        recordBtn.addEventListener('click', async function () {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                mediaRecorder.ondataavailable = event => { audioChunks.push(event.data); };
                mediaRecorder.onstop = () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                    const audioUrl = URL.createObjectURL(audioBlob);
                    if (playbackAudio) playbackAudio.src = audioUrl;
                    if (playbackCard) playbackCard.style.display = 'block';
                    if (comparisonSection) comparisonSection.style.display = 'block';
                    stream.getTracks().forEach(track => track.stop());
                };
                mediaRecorder.start();
                isRecording = true;
                recordBtn.style.display = 'none';
                if (stopBtn) stopBtn.style.display = 'inline-block';
            } catch (err) {
                alert('Please allow microphone access to record.');
            }
        });
    }

    if (stopBtn) {
        stopBtn.addEventListener('click', function () {
            if (mediaRecorder && isRecording) {
                mediaRecorder.stop();
                isRecording = false;
                if (recordBtn) recordBtn.style.display = 'inline-block';
                stopBtn.style.display = 'none';
            }
        });
    }

    if (yesBtn) {
        yesBtn.addEventListener('click', function () {
            recordingConfirmed = true;
            if (comparisonFeedback) comparisonFeedback.innerHTML = '<span style="color: green;">✓ Great! Your recording shows improvement.</span>';
            checkListeningCompletion();
        });
    }

    if (noBtn) {
        noBtn.addEventListener('click', function () {
            recordingConfirmed = false;
            if (comparisonFeedback) comparisonFeedback.innerHTML = '<span style="color: orange;">🔄 Please record again.</span>';
            if (playbackCard) playbackCard.style.display = 'none';
            if (comparisonSection) comparisonSection.style.display = 'none';
            if (playbackAudio) playbackAudio.src = '';
            if (recordBtn) recordBtn.style.display = 'inline-block';
            if (stopBtn) stopBtn.style.display = 'none';
            if (mediaRecorder && mediaRecorder.state === 'recording') mediaRecorder.stop();
            checkListeningCompletion();
        });
    }

    function checkQuiz() {
        const q1Selected = document.querySelector('input[name="q1"]:checked');
        const q2Selected = document.querySelector('input[name="q2"]:checked');
        const q1FeedbackEl = document.getElementById('q1Feedback');
        const q2FeedbackEl = document.getElementById('q2Feedback');

        if (q1FeedbackEl) {
            q1FeedbackEl.className = 'ind-quiz-feedback';
            if (!q1Selected) {
                q1FeedbackEl.innerHTML = '⚠️ Please select an answer.';
                q1FeedbackEl.className = 'ind-quiz-feedback incorrect';
                q1Correct = false;
            } else {
                if (q1Selected.value === pageConfig.quizAnswers.q1) {
                    q1FeedbackEl.innerHTML = '✅ Correct!';
                    q1FeedbackEl.className = 'ind-quiz-feedback correct';
                    q1Correct = true;
                } else {
                    q1FeedbackEl.innerHTML = `❌ Incorrect. The correct answer is "${pageConfig.quizAnswers.q1}".`;
                    q1FeedbackEl.className = 'ind-quiz-feedback incorrect';
                    q1Correct = false;
                }
            }
        }

        if (q2FeedbackEl) {
            q2FeedbackEl.className = 'ind-quiz-feedback';
            if (!q2Selected) {
                q2FeedbackEl.innerHTML = '⚠️ Please select an answer.';
                q2FeedbackEl.className = 'ind-quiz-feedback incorrect';
                q2Correct = false;
            } else {
                if (q2Selected.value === pageConfig.quizAnswers.q2) {
                    q2FeedbackEl.innerHTML = '✅ Correct!';
                    q2FeedbackEl.className = 'ind-quiz-feedback correct';
                    q2Correct = true;
                } else {
                    q2FeedbackEl.innerHTML = `❌ Incorrect. The correct answer is "${pageConfig.quizAnswers.q2}".`;
                    q2FeedbackEl.className = 'ind-quiz-feedback incorrect';
                    q2Correct = false;
                }
            }
        }
        return q1Correct && q2Correct;
    }

    if (checkBtn) {
        checkBtn.addEventListener('click', function () {
            if (checkQuiz()) {
                quizCompleted = true;
                if (quizFeedback) {
                    quizFeedback.innerHTML = '✅ Great job! Both answers are correct!';
                    quizFeedback.className = 'quiz-feedback correct';
                }
                checkListeningCompletion();
            } else {
                quizCompleted = false;
                if (quizFeedback) {
                    quizFeedback.innerHTML = '❌ Please correct the answers shown above.';
                    quizFeedback.className = 'quiz-feedback incorrect';
                }
                checkListeningCompletion();
            }
        });
    }

    function checkListeningCompletion() {
        if (completeListeningBtn) {
            if (quizCompleted && recordingConfirmed) {
                completeListeningBtn.disabled = false;
            } else {
                completeListeningBtn.disabled = true;
            }
        }
    }

    if (completeListeningBtn) {
        completeListeningBtn.addEventListener('click', function () {
            if (!completeListeningBtn.disabled) {
                const checklistId = completeListeningBtn.getAttribute('data-checklist');
                completeListeningBtn.disabled = true;
                if (checklistId) {
                    markActivityComplete('listening', checklistId);
                } else {
                    markActivityComplete('listening', 'chk4');
                }
            }
        });
    }
}

// ==================== BLOCK 3: VOCABULARY ACTIVITY (OPTIONAL) ====================
// UPDATED: ONLY audio checkmarks required - NO power word dependency

function initVocabularyActivity() {
    const vocabCompleteBtn = document.getElementById('completeVocabularyBtn');
    const vocabAudioBtns = document.querySelectorAll('.vocab-audio-btn');
    const vocabCheckStatus = {};

    pageConfig.vocabularyWords.forEach(word => {
        vocabCheckStatus[`check-${word.toLowerCase()}`] = false;
    });

    function checkVocabAllCompleted() {
        const allChecked = Object.values(vocabCheckStatus).every(v => v === true);

        if (vocabCompleteBtn) {
            if (allChecked) {
                vocabCompleteBtn.disabled = false;
            } else {
                vocabCompleteBtn.disabled = true;
            }
        }
    }

    function updateVocabCheckMark(checkId) {
        if (!vocabCheckStatus[checkId]) {
            vocabCheckStatus[checkId] = true;
            const cell = document.getElementById(checkId);
            if (cell) {
                cell.innerHTML = '✅';
                cell.style.color = 'green';
            }
            checkVocabAllCompleted();
        }
    }

    vocabAudioBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            const word = this.getAttribute('data-word');
            const checkId = this.getAttribute('data-checkid');
            if ('speechSynthesis' in window) {
                window.speechSynthesis.cancel();
                const utterance = new SpeechSynthesisUtterance(word);
                utterance.lang = 'en-US';
                utterance.rate = 0.9;
                utterance.onend = () => {
                    if (checkId) updateVocabCheckMark(checkId);
                };
                window.speechSynthesis.speak(utterance);
            } else {
                if (checkId) updateVocabCheckMark(checkId);
            }
        });
    });

    if (vocabCompleteBtn) {
        vocabCompleteBtn.addEventListener('click', function () {
            if (!vocabCompleteBtn.disabled) {
                const checklistId = vocabCompleteBtn.getAttribute('data-checklist');
                vocabCompleteBtn.disabled = true;
                if (checklistId) {
                    markActivityComplete('vocabulary', checklistId);
                } else {
                    markActivityComplete('vocabulary', 'chk3');
                }
            }
        });
    }
}

// ==================== BLOCK 4: GRAMMAR ACTIVITY (OPTIONAL) ====================

function initGrammarActivity() {
    let grammarOk = false;

    const checkGrammarBtn = document.getElementById('checkGrammarBtn');
    if (checkGrammarBtn) {
        checkGrammarBtn.addEventListener('click', () => {
            // Get all grammar inputs (supports 3 or 4 questions)
            const grammarInputs = document.querySelectorAll('.grammar-input');
            let allValid = true;

            grammarInputs.forEach((input, index) => {
                const value = input.value.trim();
                const qNum = index + 1;
                const qConfig = pageConfig.grammarAnswers[`q${qNum}`];
                const fb = document.getElementById(`grammar${qNum}Feedback`);

                let isValid = false;
                if (qConfig && qConfig.keyword) {
                    isValid = value.toLowerCase().includes(qConfig.keyword);
                } else {
                    isValid = value.length > 10;
                }

                if (fb) {
                    if (isValid) {
                        fb.innerHTML = qConfig?.message || '✅ Correct!';
                        fb.className = 'fix-feedback correct';
                    } else {
                        fb.innerHTML = qConfig?.errorMessage || '❌ Incorrect. Please check your answer.';
                        fb.className = 'fix-feedback incorrect';
                        allValid = false;
                    }
                }
            });

            const grammarFeedback = document.getElementById('grammarFeedback');
            const completeGrammarBtn = document.getElementById('completeGrammarBtn');

            if (allValid) {
                grammarOk = true;
                if (grammarFeedback) {
                    grammarFeedback.innerHTML = '✅ All answers correct! Great job!';
                    grammarFeedback.className = 'quiz-feedback correct';
                }
                if (completeGrammarBtn) completeGrammarBtn.disabled = false;
            } else {
                grammarOk = false;
                if (grammarFeedback) {
                    grammarFeedback.innerHTML = '❌ Please correct the errors above.';
                    grammarFeedback.className = 'quiz-feedback incorrect';
                }
            }
        });
    }

    const resetGrammarBtn = document.getElementById('resetGrammarBtn');
    if (resetGrammarBtn) {
        resetGrammarBtn.addEventListener('click', () => {
            const grammarInputs = document.querySelectorAll('.grammar-input');
            grammarInputs.forEach(input => {
                if (input) input.value = '';
            });
            grammarOk = false;
            const completeGrammarBtn = document.getElementById('completeGrammarBtn');
            if (completeGrammarBtn) completeGrammarBtn.disabled = true;
            const grammarFeedback = document.getElementById('grammarFeedback');
            if (grammarFeedback) grammarFeedback.innerHTML = '';
            for (let i = 1; i <= 4; i++) {
                const fb = document.getElementById(`grammar${i}Feedback`);
                if (fb) fb.innerHTML = '';
            }
        });
    }

    const completeGrammarBtn = document.getElementById('completeGrammarBtn');
    if (completeGrammarBtn) {
        completeGrammarBtn.addEventListener('click', () => {
            if (grammarOk) {
                const checklistId = completeGrammarBtn.getAttribute('data-checklist');
                if (checklistId) {
                    markActivityComplete('grammar', checklistId);
                } else {
                    markActivityComplete('grammar', 'chk5');
                }
            }
        });
    }
}

// ==================== BLOCK 5: MAIN INITIALIZATION (AUTO-DETECT) ====================

function initializeDay(day, level, config) {
    currentDay = day;
    currentLevel = level;
    pageConfig = config;

    // Reset activity completed status for new day
    activityCompleted = {
        listening: false,
        vocabulary: false,
        grammar: false
    };

    // Reset window flags
    window.speakingCompleted = false;
    window.readingCompleted = false;

    // Auto-detect and initialize ONLY if elements exist
    if (document.getElementById('listeningAudio')) {
        initListeningActivity();
    }

    if (document.getElementById('vocabulary-card')) {
        initVocabularyActivity();
    }

    if (document.getElementById('grammar-card')) {
        initGrammarActivity();
    }

    // Setup day complete button
    const dayCompleteBtn = document.getElementById('dayCompleteBtn');
    if (dayCompleteBtn) dayCompleteBtn.addEventListener('click', completeDay);

    updateChecklistProgress();

    // Initialize localStorage for this day and restore any saved progress
    initProgressStorage(day, level);
    loadProgress();

    // Auto-save on every input/textarea change
    document.querySelectorAll('input[type="text"], input[type="email"], textarea').forEach(el => {
        el.addEventListener('input', saveProgress);
    });
}

// Export for use in HTML
window.initializeDay = initializeDay;
window.markActivityComplete = markActivityComplete;
window.updateChecklistProgress = updateChecklistProgress;

// ==================== BLOCK 6: COMMON UTILITY FUNCTIONS ====================
// These functions are used across multiple day files

/**
 * Format seconds into MM:SS display string
 * @param {number} seconds
 * @returns {string} formatted time e.g. "01:30"
 */
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Show a validation/status message in a given element
 * @param {string} elementId - ID of the element to show the message in
 * @param {string} message - Message text to display
 * @param {string} type - 'success' | 'error' | 'warning' | 'info' (default: 'info')
 * @param {number} autohideMs - Auto-hide after ms (0 = no auto-hide, default: 0)
 */
function showValidationMessage(elementId, message, type = 'info', autohideMs = 0) {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = message;
        el.style.display = 'block';
        // Remove all type classes then add correct one
        el.classList.remove('success', 'error', 'warning', 'info');
        el.classList.add(type);
        if (autohideMs > 0) {
            setTimeout(() => { el.style.display = 'none'; }, autohideMs);
        }
    } else {
        // Fallback if element not found
        if (type === 'error') console.warn(message);
    }
}

/**
 * Hide a validation message element
 * @param {string} elementId - ID of the element to hide
 */
function hideValidationMessage(elementId) {
    const el = document.getElementById(elementId);
    if (el) el.style.display = 'none';
}

/**
 * Speak a word using browser Speech Synthesis API
 * @param {string} word - The word/phrase to speak
 * @param {string} lang - Language code (default: 'en-US')
 * @param {number} rate - Speech rate (default: 0.9)
 * @param {Function} onEnd - Callback after speech ends (optional)
 */
function speakWord(word, lang = 'en-US', rate = 0.9, onEnd = null) {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(word);
        utterance.lang = lang;
        utterance.rate = rate;
        if (onEnd) utterance.onend = onEnd;
        window.speechSynthesis.speak(utterance);
    } else {
        if (onEnd) onEnd(); // Call callback even if TTS not available
    }
}

/**
 * Initialize a generic speaking recorder with timer and duration validation.
 * Handles: start, stop, playback, status indicator, and completing the activity.
 *
 * @param {Object} config - Configuration object:
 *   - recordBtnId {string}: ID of the record start button
 *   - stopBtnId {string}: ID of the stop button
 *   - statusId {string}: ID of the recording status indicator div
 *   - timerId {string}: ID of the timer display span
 *   - playbackAreaId {string}: ID of the playback area div
 *   - playbackAudioId {string}: ID of the playback audio element
 *   - completeBtnId {string}: ID of the complete activity button
 *   - validationMsgId {string}: ID of the validation message div
 *   - minDuration {number}: Minimum acceptable duration in seconds (default: 30)
 *   - targetDuration {number}: Target/ideal duration in seconds (default: 60)
 *   - onComplete {Function}: Callback when the complete button is clicked successfully
 */
function initSpeakingRecorder(config) {
    const {
        recordBtnId,
        stopBtnId,
        statusId,
        timerId,
        playbackAreaId,
        playbackAudioId,
        completeBtnId,
        validationMsgId,
        minDuration = 30,
        targetDuration = 60,
        onComplete = null
    } = config;

    const recordBtn = document.getElementById(recordBtnId);
    const stopBtn = document.getElementById(stopBtnId);
    const statusEl = document.getElementById(statusId);
    const timerEl = document.getElementById(timerId);
    const playbackArea = document.getElementById(playbackAreaId);
    const playbackAudio = document.getElementById(playbackAudioId);
    const completeBtn = document.getElementById(completeBtnId);
    const validationEl = document.getElementById(validationMsgId);

    let mediaRecorder = null;
    let audioChunks = [];
    let isRecording = false;
    let timerInterval = null;
    let recordingSeconds = 0;
    let recordingDuration = 0;
    let speakingRecorded = false;
    let speakingValidated = false;

    function showMsg(msg, type = 'info', autohide = 0) {
        if (validationEl) {
            validationEl.textContent = msg;
            validationEl.style.display = 'block';
            validationEl.classList.remove('success', 'error', 'warning', 'info');
            validationEl.classList.add(type);
            if (autohide > 0) setTimeout(() => { validationEl.style.display = 'none'; }, autohide);
        }
    }

    function hideMsg() {
        if (validationEl) validationEl.style.display = 'none';
    }

    function startTimer() {
        recordingSeconds = 0;
        if (timerEl) timerEl.textContent = formatTime(0);
        timerInterval = setInterval(() => {
            recordingSeconds++;
            if (timerEl) timerEl.textContent = formatTime(recordingSeconds);
            // Auto-stop at target duration
            if (recordingSeconds >= targetDuration) {
                if (mediaRecorder && isRecording) stopRecording();
            }
        }, 1000);
    }

    function stopTimer() {
        if (timerInterval) { clearInterval(timerInterval); timerInterval = null; }
    }

    function validateDuration(dur) {
        if (completeBtn) completeBtn.disabled = true;
        if (dur >= targetDuration * 0.94) { // ~94% of target is acceptable
            showMsg(`✅ Excellent! Recording: ${formatTime(dur)}. Perfect!`, 'success', 5000);
            speakingValidated = true;
            if (completeBtn) completeBtn.disabled = false;
        } else if (dur >= minDuration) {
            showMsg(`⚠️ Good start! ${formatTime(dur)} recorded. Try to reach ${formatTime(targetDuration)}.`, 'warning');
            speakingValidated = false;
        } else if (dur > 0) {
            showMsg(`❌ Too short! Only ${formatTime(dur)}. Please record at least ${formatTime(minDuration)}.`, 'error');
            speakingValidated = false;
        } else {
            showMsg(`❌ No recording detected. Please click the record button.`, 'error');
            speakingValidated = false;
        }
    }

    function stopRecording() {
        if (mediaRecorder && isRecording) {
            mediaRecorder.stop();
            isRecording = false;
            stopTimer();
            recordingDuration = recordingSeconds;
            if (statusEl) statusEl.style.display = 'none';
            if (recordBtn) recordBtn.style.display = 'inline-flex';
            if (stopBtn) stopBtn.style.display = 'none';
        }
    }

    if (recordBtn) {
        recordBtn.addEventListener('click', async function () {
            try {
                speakingValidated = false;
                speakingRecorded = false;
                recordingDuration = 0;
                hideMsg();
                if (completeBtn) completeBtn.disabled = true;
                if (playbackArea) playbackArea.style.display = 'none';

                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
                mediaRecorder.onstop = () => {
                    const blob = new Blob(audioChunks, { type: 'audio/webm' });
                    const url = URL.createObjectURL(blob);
                    if (playbackAudio) { playbackAudio.src = url; playbackAudio.load(); }
                    if (playbackArea) { playbackArea.style.display = 'block'; }
                    speakingRecorded = true;
                    validateDuration(recordingDuration);
                    stream.getTracks().forEach(t => t.stop());
                };
                mediaRecorder.start();
                isRecording = true;
                if (statusEl) statusEl.style.display = 'flex';
                startTimer();
                recordBtn.style.display = 'none';
                if (stopBtn) stopBtn.style.display = 'inline-flex';
                showMsg(`🎤 Recording in progress... Aim for ${formatTime(targetDuration)}.`, 'info');
            } catch (e) {
                console.error('Microphone error:', e);
                alert('Unable to access microphone. Please check your permissions.');
            }
        });
    }

    if (stopBtn) {
        stopBtn.addEventListener('click', function () {
            if (mediaRecorder && isRecording) stopRecording();
        });
    }

    if (completeBtn) {
        completeBtn.addEventListener('click', function () {
            if (!completeBtn.disabled && speakingRecorded && speakingValidated) {
                window.speakingCompleted = true;
                if (onComplete) onComplete();
                showMsg('✅ Speaking activity completed! Great job!', 'success', 5000);
            } else if (!speakingRecorded) {
                showMsg('⚠️ Please record your speaking first.', 'warning');
            } else if (!speakingValidated) {
                showMsg(`⚠️ Your recording needs to be longer. Try to reach ${formatTime(targetDuration)}.`, 'warning');
            }
        });
    }

    // Return state accessor for external use
    return {
        isRecorded: () => speakingRecorded,
        isValidated: () => speakingValidated,
        stopRecording
    };
}

// Export common utilities
window.formatTime = formatTime;
window.showValidationMessage = showValidationMessage;
window.hideValidationMessage = hideValidationMessage;
window.speakWord = speakWord;
window.initSpeakingRecorder = initSpeakingRecorder;

// ==================== BLOCK 7: LOCALSTORAGE PROGRESS PERSISTENCE ====================
// Persists completed activity state + input values across page refreshes.
// User ID is read from <meta name="user-id" content="{{ request.user.id }}">
// set in the HTML template — keeps Django template tags out of static JS files.

let _STORAGE_KEY = '';

/**
 * Build and store the unique cache key for this user+level+day.
 * Called once at the start of initializeDay().
 */
function initProgressStorage(day, level) {
    const metaUserId = document.querySelector('meta[name="user-id"]')?.content;
    const userId = (metaUserId && metaUserId !== 'None' && metaUserId !== '')
        ? metaUserId
        : 'guest';
    _STORAGE_KEY = `progress_${userId}_${level}_day_${day}`;
}

/**
 * Save current activity completion state and all text input values to localStorage.
 */
function saveProgress() {
    if (!_STORAGE_KEY) return;

    // Collect all text inputs and textareas that have IDs
    const inputs = {};
    document.querySelectorAll('input[type="text"], input[type="email"], textarea').forEach(el => {
        if (el.id && el.value) inputs[el.id] = el.value;
    });

    const data = {
        completed: { ...activityCompleted },
        speakingCompleted: window.speakingCompleted === true,
        readingCompleted: window.readingCompleted === true,
        inputs: inputs,
        savedAt: Date.now()
    };

    try {
        localStorage.setItem(_STORAGE_KEY, JSON.stringify(data));
    } catch (e) {
        console.warn('localStorage save failed:', e);
    }
}

/**
 * Restore activity completion state and input values from localStorage.
 * Called at the end of initializeDay() after all activity init.
 */
function loadProgress() {
    if (!_STORAGE_KEY) return;

    const saved = localStorage.getItem(_STORAGE_KEY);
    if (!saved) return;

    try {
        const data = JSON.parse(saved);

        // --- Restore completed activities ---
        if (data.completed) {
            // Map activityId -> the checklist checkbox IDs used across days
            const checklistMap = {
                listening: ['chk1', 'chkListening'],
                vocabulary: ['chk4', 'chkVocabulary'],
                grammar: ['chk5', 'chkGrammar']
            };

            Object.keys(data.completed).forEach(act => {
                if (!data.completed[act]) return;

                activityCompleted[act] = true;

                // Tick the checklist checkbox (try multiple possible IDs)
                (checklistMap[act] || []).forEach(chkId => {
                    const chk = document.getElementById(chkId);
                    if (chk) chk.checked = true;
                });

                // Mark the complete button as done
                const btnId = `complete${act.charAt(0).toUpperCase() + act.slice(1)}Btn`;
                const btn = document.getElementById(btnId);
                if (btn) {
                    btn.classList.add('completed');
                    btn.textContent = '✓ Completed';
                    btn.disabled = true;
                }
            });
        }

        // --- Restore speaking/reading flags (set by day-specific code) ---
        if (data.speakingCompleted) {
            window.speakingCompleted = true;
            ['chk2', 'chkSpeaking'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.checked = true;
            });
            // Mark speaking complete button if present
            const speakBtn = document.getElementById('completeSpeakingBtn') ||
                document.getElementById('completeRecordingBtn');
            if (speakBtn) {
                speakBtn.classList.add('completed');
                speakBtn.textContent = '✓ Completed';
                speakBtn.disabled = true;
            }
        }

        if (data.readingCompleted) {
            window.readingCompleted = true;
            ['chk3', 'chkReading'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.checked = true;
            });
            const readBtn = document.getElementById('completeReadingBtn');
            if (readBtn) {
                readBtn.classList.add('completed');
                readBtn.textContent = '✓ Completed';
                readBtn.disabled = true;
            }
        }

        // --- Restore text inputs ---
        if (data.inputs) {
            Object.keys(data.inputs).forEach(id => {
                const el = document.getElementById(id);
                if (el && data.inputs[id]) el.value = data.inputs[id];
            });
        }

        // Update progress counter after restoring state
        updateChecklistProgress();

    } catch (e) {
        console.warn('Failed to restore progress from localStorage:', e);
        localStorage.removeItem(_STORAGE_KEY);
    }
}

/**
 * Clear saved progress for this day (called when day is fully completed).
 */
function clearDayProgress() {
    if (_STORAGE_KEY) {
        localStorage.removeItem(_STORAGE_KEY);
    }
}

// Export persistence functions
window.saveProgress = saveProgress;
window.loadProgress = loadProgress;
window.clearDayProgress = clearDayProgress;
window.initProgressStorage = initProgressStorage;