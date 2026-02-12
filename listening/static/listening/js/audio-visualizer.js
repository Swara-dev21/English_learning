// Audio visualizer for wave effect
document.addEventListener('DOMContentLoaded', function() {
    const audioWave = document.querySelector('.audio-wave');
    if (audioWave) {
        // Create wave effect
        function animateWave() {
            const wave = audioWave.querySelector('.wave-animation') || document.createElement('div');
            wave.className = 'wave-animation';
            wave.style.cssText = `
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.3) 50%, transparent 100%);
                animation: waveMove 2s linear infinite;
            `;
            
            // Add style for animation
            if (!document.querySelector('#wave-style')) {
                const style = document.createElement('style');
                style.id = 'wave-style';
                style.textContent = `
                    @keyframes waveMove {
                        0% { transform: translateX(-100%); }
                        100% { transform: translateX(100%); }
                    }
                `;
                document.head.appendChild(style);
            }
            
            if (!audioWave.querySelector('.wave-animation')) {
                audioWave.appendChild(wave);
            }
        }
        
        animateWave();
    }
});