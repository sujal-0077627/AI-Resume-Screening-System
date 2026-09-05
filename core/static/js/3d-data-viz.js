/**
 * 3D Data Visualization - AI Resume Screening (Premium Edition)
 * Renders Django context data as interactive 3D charts, holographic score rings,
 * and animated counters for a premium data-driven experience.
 *
 * Uses Three.js for 3D charts and respects prefers-reduced-motion.
 */
(function () {
    'use strict';

    // Respect reduced-motion preferences
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    // ============================================================
    // 1. ANIMATED COUNTERS - Count up numbers on scroll
    // ============================================================
    function animateCounters() {
        var counters = document.querySelectorAll('.stat-value[data-count]');
        if (counters.length === 0) return;

        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    var el = entry.target;
                    var target = parseFloat(el.getAttribute('data-count')) || 0;
                    var suffix = el.getAttribute('data-suffix') || '';
                    var duration = 1200;
                    var start = performance.now();

                    function update() {
                        var elapsed = performance.now() - start;
                        var progress = Math.min(elapsed / duration, 1);
                        // Ease out cubic
                        progress = 1 - Math.pow(1 - progress, 3);
                        var value = Math.round(target * progress);
                        el.textContent = value + suffix;
                        if (progress < 1) requestAnimationFrame(update);
                    }
                    update();
                    observer.unobserve(el);
                }
            });
        }, { threshold: 0.5 });

        counters.forEach(function (el) {
            observer.observe(el);
        });
    }

    // ============================================================
    // 2. HOLOGRAPHIC SCORE RING - Animated progress ring
    // ============================================================
    function animateScoreRing() {
        var scoreCircle = document.querySelector('.score-circle');
        if (!scoreCircle) return;

        var scoreText = scoreCircle.querySelector('.score-number');
        if (!scoreText) return;

        var targetScore = parseFloat(scoreText.textContent) || 0;
        var targetAngle = (targetScore / 100) * 360;

        // Animate the conic-gradient angle
        var start = performance.now();
        var duration = 1500;

        function update() {
            var elapsed = performance.now() - start;
            var progress = Math.min(elapsed / duration, 1);
            // ease out back
            progress = 1 - Math.pow(1 - progress, 3);
            var currentAngle = targetAngle * progress;
            scoreCircle.style.setProperty('--score-angle', currentAngle + 'deg');
            if (progress < 1) requestAnimationFrame(update);
        }
        update();
    }

    // ============================================================
    // 3. 3D BAR CHART - For dashboard stats
    // ============================================================
    function create3DBarChart() {
        var container = document.getElementById('3d-chart-container');
        if (!container) return;

        // Load Three.js if not already loaded
        if (!window.THREE) return;

        var THREE = window.THREE;
        var isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);

        // Get data from data attributes
        var dataPoints = [];
        var dataEls = container.querySelectorAll('[data-value]');
        dataEls.forEach(function (el) {
            dataPoints.push({
                label: el.getAttribute('data-label') || '',
                value: parseFloat(el.getAttribute('data-value')) || 0
            });
        });

        if (dataPoints.length === 0) return;

        // Scene setup
        var scene = new THREE.Scene();
        var camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 100);
        camera.position.set(0, 8, 15);
        camera.lookAt(0, 2, 0);

        var renderer = new THREE.WebGLRenderer({
            canvas: container,
            alpha: true,
            antialias: !isMobile,
            powerPreference: 'high-performance'
        });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, isMobile ? 1.5 : 2));
        renderer.setSize(container.clientWidth, container.clientHeight);
        renderer.setClearColor(0x000000, 0);

        // Create 3D bars
        var barWidth = 1.2;
        var gap = 0.8;
        var totalWidth = dataPoints.length * (barWidth + gap) - gap;
        var startX = -totalWidth / 2;

        var bars = [];
        var barColors = [0x6c5ce7, 0x74b9ff, 0xa29bfe, 0x10b981, 0xf59e0b, 0xef4444];

        dataPoints.forEach(function (dp, idx) {
            var height = Math.max(dp.value / 100 * 6, 0.3);
            var barGeo = new THREE.BoxGeometry(barWidth, height, barWidth);
            var barMat = new THREE.MeshPhysicalMaterial({
                color: barColors[idx % barColors.length],
                emissive: barColors[idx % barColors.length],
                emissiveIntensity: 0.4,
                metalness: 0.6,
                roughness: 0.3,
                clearcoat: 0.8,
                clearcoatRoughness: 0.2,
                transparent: true,
                opacity: 0.85
            });
            var bar = new THREE.Mesh(barGeo, barMat);
            bar.position.set(startX + idx * (barWidth + gap), height / 2, 0);
            scene.add(bar);
            bars.push({ mesh: bar, targetHeight: height });
        });

        // Ground plane (subtle)
        var groundGeo = new THREE.PlaneGeometry(totalWidth + 2, 8);
        var groundMat = new THREE.MeshBasicMaterial({
            color: 0x1a202c,
            transparent: true,
            opacity: 0.3,
            side: THREE.DoubleSide
        });
        var ground = new THREE.Mesh(groundGeo, groundMat);
        ground.rotation.x = -Math.PI / 2;
        ground.position.y = 0.01;
        scene.add(ground);

        // Animation - bars grow up
        var clock = new THREE.Clock();
        var startTime = performance.now();
        var growDuration = 1500;

        function animate() {
            requestAnimationFrame(animate);

            var elapsed = clock.getElapsedTime();
            var growProgress = Math.min((performance.now() - startTime) / growDuration, 1);
            growProgress = 1 - Math.pow(1 - growProgress, 3); // easeOutCubic

            // Grow bars
            bars.forEach(function (barObj) {
                var currentHeight = barObj.targetHeight * growProgress;
                barObj.mesh.scale.y = Math.max(currentHeight / barObj.targetHeight, 0.01);
                barObj.mesh.position.y = currentHeight / 2;
            });

            // Rotate scene slowly
            scene.rotation.y = Math.sin(elapsed * 0.3) * 0.2;

            renderer.render(scene, camera);
        }
        animate();

        // Resize handling
        window.addEventListener('resize', function () {
            camera.aspect = container.clientWidth / container.clientHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(container.clientWidth, container.clientHeight);
        });
    }

    // ============================================================
    // 4. 3D SCORE HOLOGRAM - Rotating 3D ring for candidate score
    // ============================================================
    function create3DScoreHologram() {
        var container = document.getElementById('3d-score-hologram');
        if (!container) return;

        var score = parseFloat(container.getAttribute('data-score')) || 0;
        var THREE = window.THREE;
        var isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);

        // Graceful fallback: agar Three.js (CDN) load nahi hua ya WebGL
        // available nahi hai, to khali 200px box ki jagah container hide
        // kar do — isse page par extra white space nahi bachta.
        if (!THREE || !THREE.WebGLRenderer || !window.WebGLRenderingContext) {
            container.style.display = 'none';
            return;
        }

        // Renderer ke liye real <canvas> element banao — container div ko
        // directly canvas ke roop mein pass karna WebGLRenderer ko crash
        // karta tha, jisse hologram hamesha khali box hi rehta tha.
        var canvas = document.createElement('canvas');
        canvas.width = container.clientWidth || 200;
        canvas.height = container.clientHeight || 200;
        container.appendChild(canvas);

        try {
            // Scene
            var scene = new THREE.Scene();
            var camera = new THREE.PerspectiveCamera(50, canvas.width / canvas.height, 0.1, 100);
            camera.position.set(0, 0, 10);

            var renderer = new THREE.WebGLRenderer({
                canvas: canvas,
                alpha: true,
                antialias: !isMobile,
                powerPreference: 'high-performance'
            });
        } catch (err) {
            // WebGL context fail ho jaye to bhi khali box na bache
            container.style.display = 'none';
            return;
        }
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, isMobile ? 1.5 : 2));
        renderer.setSize(container.clientWidth, container.clientHeight);
        renderer.setClearColor(0x000000, 0);

        // Score ring (torus)
        var ringGeo = new THREE.TorusGeometry(3, 0.3, 16, 60);
        var ringMat = new THREE.MeshPhysicalMaterial({
            color: score >= 70 ? 0x10b981 : score >= 40 ? 0xf59e0b : 0xef4444,
            emissive: score >= 70 ? 0x10b981 : score >= 40 ? 0xf59e0b : 0xef4444,
            emissiveIntensity: 0.6,
            metalness: 0.8,
            roughness: 0.2,
            clearcoat: 1,
            clearcoatRoughness: 0.1,
            transparent: true,
            opacity: 0.9
        });
        var ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = Math.PI / 2.2;
        scene.add(ring);

        // Inner sphere (core)
        var sphereGeo = new THREE.SphereGeometry(1.5, 24, 16);
        var sphereMat = new THREE.MeshPhysicalMaterial({
            color: 0xffffff,
            emissive: score >= 70 ? 0x10b981 : score >= 40 ? 0xf59e0b : 0xef4444,
            emissiveIntensity: 1.0,
            metalness: 0.9,
            roughness: 0.1,
            clearcoat: 1,
            clearcoatRoughness: 0.05,
            transparent: true,
            opacity: 0.95
        });
        var sphere = new THREE.Mesh(sphereGeo, sphereMat);
        scene.add(sphere);

        // Sparkle particles around
        var sparkCount = isMobile ? 20 : 50;
        var sparkGeom = new THREE.BufferGeometry();
        var sparkPos = new Float32Array(sparkCount * 3);
        for (var s = 0; s < sparkCount; s++) {
            var angle = Math.random() * Math.PI * 2;
            var radius = 3.5 + Math.random() * 2;
            sparkPos[s * 3] = Math.cos(angle) * radius;
            sparkPos[s * 3 + 1] = Math.sin(angle) * radius;
            sparkPos[s * 3 + 2] = (Math.random() - 0.5) * 2;
        }
        sparkGeom.setAttribute('position', new THREE.BufferAttribute(sparkPos, 3));
        var sparkMat = new THREE.PointsMaterial({
            color: 0x74b9ff,
            size: 0.2,
            transparent: true,
            opacity: 0.7,
            depthWrite: false,
            blending: THREE.AdditiveBlending
        });
        var sparks = new THREE.Points(sparkGeom, sparkMat);
        scene.add(sparks);

        // Animation
        var clock = new THREE.Clock();

        function animate() {
            requestAnimationFrame(animate);
            var elapsed = clock.getElapsedTime();

            ring.rotation.z += 0.01;
            ring.rotation.x = Math.PI / 2.2 + Math.sin(elapsed * 0.5) * 0.1;
            sphere.rotation.y += 0.005;
            sphere.rotation.x += 0.003;

            // Sparkles orbit
            var sparkAttr = sparkGeom.attributes.position;
            var sparkArr = sparkAttr.array;
            for (var sp = 0; sp < sparkCount; sp++) {
                var a = Math.atan2(sparkArr[sp * 3 + 1], sparkArr[sp * 3]) + 0.01;
                var r = Math.sqrt(sparkArr[sp * 3] * sparkArr[sp * 3] + sparkArr[sp * 3 + 1] * sparkArr[sp * 3 + 1]);
                sparkArr[sp * 3] = Math.cos(a) * r;
                sparkArr[sp * 3 + 1] = Math.sin(a) * r;
            }
            sparkAttr.needsUpdate = true;

            renderer.render(scene, camera);
        }
        animate();

        // Resize
        window.addEventListener('resize', function () {
            camera.aspect = container.clientWidth / container.clientHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(container.clientWidth, container.clientHeight);
        });
    }

    // ============================================================
    // INITIALIZE ALL VISUALIZATIONS
    // ============================================================
    document.addEventListener('DOMContentLoaded', function () {
        animateCounters();
        animateScoreRing();
        create3DBarChart();
        create3DScoreHologram();
    });
})();