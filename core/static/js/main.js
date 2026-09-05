// ===== AI Resume Screening System - Main JavaScript =====

document.addEventListener('DOMContentLoaded', function() {
    // Mark JS as active so reveal-on-scroll only hides when JS works
    document.body.classList.add('js-enabled');

    const themeToggle = document.getElementById('themeToggle');
    const html = document.documentElement;

    // Load saved theme from localStorage
    const savedTheme = localStorage.getItem('theme') || 'light';
    html.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);

    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const currentTheme = html.getAttribute('data-theme');
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            html.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeIcon(newTheme);
        });
    }

    // Set score circle angle
    const scoreCircle = document.querySelector('.score-circle');
    if (scoreCircle) {
        const scoreText = scoreCircle.querySelector('.score-number');
        if (scoreText) {
            const score = parseFloat(scoreText.textContent) || 0;
            const angle = (score / 100) * 360;
            scoreCircle.style.setProperty('--score-angle', angle + 'deg');
        }
    }

    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        document.querySelectorAll('.alert-dismissible').forEach(function(alert) {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        });
    }, 5000);

    // ============================================================
    // PREMIUM 3D EXPERIENCE LAYER
    // Scroll reveal + 3D tilt + holographic glow integration
    // ============================================================

    // 1. Add cinematic entrance to main page content
    const mainContent = document.querySelector('main');
    if (mainContent) {
        mainContent.classList.add('cinematic-in');
    }

    // 2. Enhance stat cards / action cards / job cards with holo effect
    document.querySelectorAll('.stat-card, .action-card, .job-card').forEach(function(card) {
        card.classList.add('holo-card');
    });

    // 3. Scroll-triggered reveal using IntersectionObserver
    const revealElements = document.querySelectorAll('.reveal-on-scroll');
    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('revealed');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });

        revealElements.forEach(function(el) {
            observer.observe(el);
        });
    } else {
        // Fallback: show everything immediately
        revealElements.forEach(function(el) {
            el.classList.add('revealed');
        });
    }

    // 4. 3D tilt effect on interactive cards (desktop only, respects reduced motion)
    const reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const isTouchDevice = (window.matchMedia && window.matchMedia('(hover: none)').matches) ||
                          /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);

    if (!reduceMotion && !isTouchDevice) {
        const tiltTargets = document.querySelectorAll('.stat-card, .action-card, .job-card, .card-custom');

        tiltTargets.forEach(function(card) {
            card.classList.add('tilt-3d');

            card.addEventListener('mousemove', function(e) {
                const rect = card.getBoundingClientRect();
                const x = (e.clientX - rect.left) / rect.width - 0.5;
                const y = (e.clientY - rect.top) / rect.height - 0.5;

                const rotateY = x * 8;   // max ~4deg each side
                const rotateX = -y * 8;

                card.style.transform = 'perspective(900px) rotateX(' + rotateX + 'deg) rotateY(' + rotateY + 'deg) translateY(-2px)';
                card.style.transition = 'transform 0.1s ease-out';
            });

            card.addEventListener('mouseleave', function() {
                card.style.transform = 'perspective(900px) rotateX(0deg) rotateY(0deg) translateY(0)';
                card.style.transition = 'transform 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
            });
        });
    }

    // 5. Canvas opacity adjusts with theme (subtle premium feel)
    const bgCanvas = document.getElementById('bg-3d-canvas');
    if (bgCanvas) {
        const applyThemeOpacity = function() {
            const theme = html.getAttribute('data-theme');
            bgCanvas.style.opacity = theme === 'dark' ? '0.7' : '0.55';
        };
        applyThemeOpacity();

        if (themeToggle) {
            themeToggle.addEventListener('click', applyThemeOpacity);
        }
    }

    // ============================================================
    // PREMIUM MICRO-INTERACTIONS (Phase 7)
    // Magnetic buttons + 3D cursor trail + touch feedback
    // ============================================================

    // 6. Magnetic buttons - buttons subtly attract toward cursor
    if (!isTouchDevice && !reduceMotion) {
        const magneticElements = document.querySelectorAll('.btn-primary, .btn-lg, .login-btn');
        magneticElements.forEach(function(btn) {
            btn.addEventListener('mousemove', function(e) {
                const rect = btn.getBoundingClientRect();
                const x = e.clientX - rect.left - rect.width / 2;
                const y = e.clientY - rect.top - rect.height / 2;
                btn.style.transform = 'translate(' + x * 0.15 + 'px, ' + y * 0.15 + 'px)';
                btn.style.transition = 'transform 0.1s ease-out';
            });
            btn.addEventListener('mouseleave', function() {
                btn.style.transform = 'translate(0, 0)';
                btn.style.transition = 'transform 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
            });
        });
    }

    // 7. 3D Cursor trail - subtle glowing particles follow cursor (desktop only)
    if (!isTouchDevice && !reduceMotion) {
        const cursorTrail = document.createElement('div');
        cursorTrail.id = 'cursor-trail';
        cursorTrail.style.cssText = 'position:fixed;width:8px;height:8px;border-radius:50%;pointer-events:none;z-index:9999;' +
            'background:radial-gradient(circle, rgba(108,92,231,0.8), rgba(116,185,255,0.2));' +
            'box-shadow:0 0 12px rgba(108,92,231,0.6);transition:opacity 0.3s;opacity:0;';
        document.body.appendChild(cursorTrail);

        document.addEventListener('mousemove', function(e) {
            cursorTrail.style.left = (e.clientX - 4) + 'px';
            cursorTrail.style.top = (e.clientY - 4) + 'px';
            cursorTrail.style.opacity = '1';
        });

        document.addEventListener('mouseleave', function() {
            cursorTrail.style.opacity = '0';
        });
    }

    // 8. Touch feedback - tactile response on mobile
    if (isTouchDevice) {
        const touchTargets = document.querySelectorAll('.stat-card, .action-card, .job-card, .btn');
        touchTargets.forEach(function(el) {
            el.addEventListener('touchstart', function() {
                el.style.transform = 'scale(0.97)';
                el.style.transition = 'transform 0.1s ease';
            });
            el.addEventListener('touchend', function() {
                el.style.transform = 'scale(1)';
                el.style.transition = 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
            });
        });
    }
});

function updateThemeIcon(theme) {
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        if (theme === 'dark') {
            themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
        } else {
            themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
        }
    }
}