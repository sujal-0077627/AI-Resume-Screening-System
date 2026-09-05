/**
 * GSAP Scroll Animations - AI Resume Screening (Premium Edition)
 * Cinematic scroll-triggered animations, parallax layers, and smooth
 * section transitions for a premium 3D experience.
 *
 * Loads GSAP + ScrollTrigger from CDN and applies elegant animations
 * to page content. Respects prefers-reduced-motion.
 */
(function () {
    'use strict';

    // Respect reduced-motion preferences
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    // Load GSAP + ScrollTrigger dynamically
    function loadScript(src, cb) {
        var script = document.createElement('script');
        script.src = src;
        script.onload = cb;
        script.onerror = function () {
            console.warn('[GSAP] Failed to load ' + src);
        };
        document.head.appendChild(script);
    }

    loadScript('https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js', function () {
        loadScript('https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/ScrollTrigger.min.js', function () {
            if (!window.gsap || !window.ScrollTrigger) return;

            var gsap = window.gsap;
            var ScrollTrigger = window.ScrollTrigger;
            gsap.registerPlugin(ScrollTrigger);

            // ============================================================
            // 1. Cinematic entrance for main content
            // ============================================================
            var mainContent = document.querySelector('main');
            if (mainContent) {
                gsap.from(mainContent, {
                    opacity: 0,
                    y: 40,
                    scale: 0.98,
                    filter: 'blur(8px)',
                    duration: 0.8,
                    ease: 'power3.out'
                });
            }

            // ============================================================
            // 2. Section reveal animations (fade + slide + scale)
            // ============================================================
            var revealTargets = document.querySelectorAll('.reveal-on-scroll, .stat-card, .action-card, .job-card, .card-custom');

            revealTargets.forEach(function (el) {
                gsap.from(el, {
                    scrollTrigger: {
                        trigger: el,
                        start: 'top 85%',
                        end: 'top 40%',
                        scrub: true
                    },
                    opacity: 0,
                    y: 40,
                    scale: 0.95,
                    duration: 0.6,
                    ease: 'power2.out'
                });
            });

            // ============================================================
            // 3. Parallax depth effect on page titles
            // ============================================================
            var pageTitles = document.querySelectorAll('.page-title');
            pageTitles.forEach(function (title) {
                gsap.from(title, {
                    scrollTrigger: {
                        trigger: title,
                        start: 'top 90%',
                        end: 'top 60%',
                        scrub: true
                    },
                    y: 20,
                    opacity: 0,
                    duration: 0.5,
                    ease: 'power2.out'
                });
            });

            // ============================================================
            // 4. Dashboard hero - cinematic entrance
            // ============================================================
            var hero = document.querySelector('.dashboard-hero');
            if (hero) {
                gsap.from(hero, {
                    opacity: 0,
                    y: 50,
                    scale: 0.95,
                    filter: 'blur(10px)',
                    duration: 1.0,
                    ease: 'power3.out'
                });
            }

            // ============================================================
            // 5. Score circle - holographic reveal
            // ============================================================
            var scoreCircle = document.querySelector('.score-circle');
            if (scoreCircle) {
                gsap.from(scoreCircle, {
                    scrollTrigger: {
                        trigger: scoreCircle,
                        start: 'top 85%',
                        end: 'top 50%',
                        scrub: true
                    },
                    scale: 0.5,
                    opacity: 0,
                    rotation: -15,
                    duration: 0.8,
                    ease: 'back.out(1.5)'
                });
            }

            // ============================================================
            // 6. Table rows - always visible (no hiding animation)
            // ============================================================
            // Table rows are always visible to ensure data is never hidden
            // (removed opacity:0 animation that could leave rows invisible)

            // ============================================================
            // 7. Navbar - subtle slide down on load
            // ============================================================
            var navbar = document.querySelector('.navbar-custom');
            if (navbar) {
                gsap.from(navbar, {
                    y: -20,
                    opacity: 0,
                    duration: 0.6,
                    ease: 'power2.out'
                });
            }

            // ============================================================
            // 8. Login card - premium entrance
            // ============================================================
            var loginCard = document.querySelector('.login-card');
            if (loginCard) {
                gsap.from(loginCard, {
                    opacity: 0,
                    y: 40,
                    scale: 0.95,
                    filter: 'blur(6px)',
                    duration: 0.8,
                    ease: 'power3.out'
                });
            }

            // ============================================================
            // 9. Floating depth layers (parallax on scroll)
            // ============================================================
            var depthElements = document.querySelectorAll('.depth-1, .depth-2, .depth-3');
            depthElements.forEach(function (el) {
                var depth = parseInt(el.className.match(/depth-(\d)/)[1] || '1', 10);
                gsap.to(el, {
                    scrollTrigger: {
                        trigger: el,
                        start: 'top bottom',
                        end: 'bottom top',
                        scrub: true
                    },
                    y: depth * 20,
                    ease: 'none'
                });
            });

            // ============================================================
            // 10. Glow border - subtle pulse on hover
            // ============================================================
            var glowElements = document.querySelectorAll('.glow-border');
            glowElements.forEach(function (el) {
                el.addEventListener('mouseenter', function () {
                    gsap.to(el, { scale: 1.02, duration: 0.3, ease: 'power2.out' });
                });
                el.addEventListener('mouseleave', function () {
                    gsap.to(el, { scale: 1, duration: 0.3, ease: 'power2.out' });
                });
            });

            // Refresh ScrollTrigger after setup
            ScrollTrigger.refresh();
        });
    });
})();