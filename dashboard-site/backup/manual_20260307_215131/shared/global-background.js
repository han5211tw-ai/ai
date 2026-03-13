/**
 * Dashboard Global Background Effects
 * Version: 20250304-2121
 * Description: Floating particles and background effects for all pages
 */

(function() {
    'use strict';
    
    // Create background elements when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        createBackgroundElements();
    });
    
    function createBackgroundElements() {
        // Check if already exists
        if (document.querySelector('.grid-bg')) return;
        
        // Create grid background
        const gridBg = document.createElement('div');
        gridBg.className = 'grid-bg';
        document.body.insertBefore(gridBg, document.body.firstChild);
        
        // Create particles container
        const particlesContainer = document.createElement('div');
        particlesContainer.className = 'particles';
        document.body.insertBefore(particlesContainer, document.body.firstChild);
        
        // Create particles (reduced count for performance: 30 instead of 50)
        const particleCount = 30;
        for (let i = 0; i < particleCount; i++) {
            createParticle(particlesContainer, i);
        }
    }
    
    function createParticle(container, index) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        
        // Random position
        const x = Math.random() * 100;
        const y = Math.random() * 100;
        
        // Random animation delay
        const delay = Math.random() * 25;
        
        // Random animation duration
        const duration = 20 + Math.random() * 10;
        
        // Random color (cyan, purple, or orange)
        const colors = ['#00f5ff', '#b347ff', '#ff6b35'];
        const color = colors[Math.floor(Math.random() * colors.length)];
        
        particle.style.left = x + '%';
        particle.style.top = y + '%';
        particle.style.animationDelay = delay + 's';
        particle.style.animationDuration = duration + 's';
        particle.style.background = color;
        particle.style.boxShadow = `0 0 10px ${color}`;
        
        container.appendChild(particle);
    }
})();