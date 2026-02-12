let mediaRecorder;
let audioChunks = [];
let audioBlob;

function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];
            mediaRecorder.start();
            document.getElementById("status").style.display = "block";

            mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
            mediaRecorder.onstop = () => {
                audioBlob = new Blob(audioChunks, { type: "audio/webm" });
            };
        })
        .catch(err => alert("Microphone error: " + err));
}

function stopRecording() {
    if (!mediaRecorder) return alert("Recording not started!");
    mediaRecorder.stop();
    document.getElementById("status").style.display = "none";

    setTimeout(() => {
        if (!audioBlob) return;
        const formData = new FormData();
        formData.append("audio", audioBlob, "recording.webm");

        fetch(`/speaking/record/${questionIndex}/`, { method: "POST", body: formData })
        .then(res => res.json())
        .then(data => {
            if (data.next_url) window.location.href = data.next_url;
            else alert("Error: " + data.error);
        })
        .catch(err => {
            console.error(err);
            alert("Upload failed");
        });
    }, 300);
}
