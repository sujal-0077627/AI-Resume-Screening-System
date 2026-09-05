/**
 * Immersive 3D Background - AI Resume Screening (Premium Edition)
 * Enhanced with custom materials, bloom-like glow effects, iridescent crystal,
 * and advanced particle systems for a truly cinematic futuristic experience.
 *
 * The scene degrades gracefully: if WebGL is not available or the user
 * prefers reduced motion, we disable 3D rendering entirely.
 */
(function () {
    'use strict';

    // --- Device capability detection & graceful degradation ---
    if (!window.requestAnimationFrame) return;
    if (typeof window.WebGLRenderingContext === 'undefined') return;
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    var canvas = document.getElementById('bg-3d-canvas');
    if (!canvas) return;

    // --- Load Three.js dynamically (kept as CDN to avoid bundling) ---
    function loadThree(cb) {
        if (window.THREE) { cb(); return; }
        var script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';
        script.onload = function () {
            if (window.THREE) cb();
            else console.warn('[3D] Three.js failed to initialize.');
        };
        script.onerror = function () {
            console.warn('[3D] Unable to load Three.js from CDN (offline?).');
        };
        document.head.appendChild(script);
    }

    loadThree(function () {
        var isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);

        // --- Scene setup ---
        var scene = new THREE.Scene();
        var camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.1, 1000);
        camera.position.z = 50;

        var renderer = new THREE.WebGLRenderer({
            canvas: canvas,
            alpha: true,
            antialias: !isMobile,
            powerPreference: 'high-performance'
        });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, isMobile ? 1.5 : 2));
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setClearColor(0x000000, 0);
        // Performance: disable shadows on mobile for better FPS
        if (!isMobile) {
            renderer.shadowMap.enabled = true;
            renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        }

        // ============================================================
        // ADAPTIVE QUALITY - FPS-based performance optimization
        // ============================================================
        var fpsHistory = [];
        var qualityScale = 1.0;
        var lastFpsTime = performance.now();
        var frameCount = 0;

        function measureFPS() {
            frameCount++;
            var now = performance.now();
            var elapsed = now - lastFpsTime;
            if (elapsed >= 1000) {
                var fps = (frameCount * 1000) / elapsed;
                fpsHistory.push(fps);
                if (fpsHistory.length > 30) fpsHistory.shift();

                // Adaptive quality: adjust pixel ratio based on FPS
                var avgFps = fpsHistory.reduce(function (a, b) { return a + b; }, 0) / fpsHistory.length;
                if (avgFps < 45 && qualityScale > 0.6) {
                    qualityScale -= 0.05;
                    renderer.setPixelRatio(Math.min(window.devicePixelRatio, isMobile ? 1.5 : 2) * qualityScale);
                }

                frameCount = 0;
                lastFpsTime = now;
            }
        }

        // ============================================================
        // ADVANCED LIGHTING - Dynamic lights for depth & realism
        // ============================================================
        // Ambient light (base illumination)
        var ambientLight = new THREE.AmbientLight(0x6c5ce7, 0.4);
        scene.add(ambientLight);

        // Main directional light (key light with shadows)
        var mainLight = new THREE.DirectionalLight(0xffffff, 1.2);
        mainLight.position.set(10, 15, 10);
        mainLight.castShadow = true;
        mainLight.shadow.mapSize.width = 1024;
        mainLight.shadow.mapSize.height = 1024;
        mainLight.shadow.camera.near = 0.5;
        mainLight.shadow.camera.far = 50;
        mainLight.shadow.camera.left = -15;
        mainLight.shadow.camera.right = 15;
        mainLight.shadow.camera.top = 15;
        mainLight.shadow.camera.bottom = -15;
        scene.add(mainLight);

        // Purple accent light (from left)
        var purpleLight = new THREE.PointLight(0x6c5ce7, 1.5, 30);
        purpleLight.position.set(-8, 3, 5);
        scene.add(purpleLight);

        // Blue accent light (from right)
        var blueLight = new THREE.PointLight(0x74b9ff, 1.2, 30);
        blueLight.position.set(8, -2, 5);
        scene.add(blueLight);

        // Pink accent light (from behind)
        var pinkLight = new THREE.PointLight(0xff6b9d, 0.8, 30);
        pinkLight.position.set(0, 5, -8);
        scene.add(pinkLight);

        // ============================================================
        // PARTICLE STARFIELD - Multi-colored with additive blending
        // ============================================================
        var particleCount = isMobile ? 400 : 1200;
        var particleGeom = new THREE.BufferGeometry();
        var positions = new Float32Array(particleCount * 3);
        var speeds = new Float32Array(particleCount);
        var colors = new Float32Array(particleCount * 3); // Per-particle colors

        for (var i = 0; i < particleCount; i++) {
            positions[i * 3] = (Math.random() - 0.5) * 240;
            positions[i * 3 + 1] = (Math.random() - 0.5) * 240;
            positions[i * 3 + 2] = (Math.random() - 0.5) * 120;
            speeds[i] = 0.005 + Math.random() * 0.02;

            // Color palette: purple, blue, pink, cyan
            var palette = Math.random();
            if (palette < 0.4) {
                colors[i * 3] = 0.42; colors[i * 3 + 1] = 0.36; colors[i * 3 + 2] = 0.91; // Purple
            } else if (palette < 0.7) {
                colors[i * 3] = 0.45; colors[i * 3 + 1] = 0.73; colors[i * 3 + 2] = 1.0; // Blue
            } else if (palette < 0.9) {
                colors[i * 3] = 1.0; colors[i * 3 + 1] = 0.55; colors[i * 3 + 2] = 0.75; // Pink
            } else {
                colors[i * 3] = 0.45; colors[i * 3 + 1] = 1.0; colors[i * 3 + 2] = 0.85; // Cyan
            }
        }
        particleGeom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        particleGeom.setAttribute('color', new THREE.BufferAttribute(colors, 3));

        var particleMat = new THREE.PointsMaterial({
            color: 0x6c5ce7,
            size: 0.18,
            vertexColors: true, // Use per-particle colors
            transparent: true,
            opacity: 0.85,
            depthWrite: false,
            blending: THREE.AdditiveBlending
        });
        var particles = new THREE.Points(particleGeom, particleMat);
        scene.add(particles);

        // ============================================================
        // CENTRAL AI CORE — Iridescent crystal with emissive glow
        // ============================================================
        var crystalGeo = new THREE.OctahedronGeometry(5.5, 0);
        var crystalMat = new THREE.MeshPhysicalMaterial({
            color: 0x6c5ce7,
            emissive: 0x6c5ce7,
            emissiveIntensity: 0.5,
            metalness: 0.85,
            roughness: 0.2,
            clearcoat: 1,
            clearcoatRoughness: 0.1,
            transparent: true,
            opacity: 0.9
        });
        var crystal = new THREE.Mesh(crystalGeo, crystalMat);
        crystal.position.set(0, -3.5, 0);
        crystal.castShadow = true;
        crystal.receiveShadow = true;
        scene.add(crystal);

        // Inner glowing core (smaller, brighter)
        var coreGeo = new THREE.IcosahedronGeometry(2.5, 0);
        var coreMat = new THREE.MeshPhysicalMaterial({
            color: 0xffffff,
            emissive: 0x6c5ce7,
            emissiveIntensity: 1.2,
            metalness: 0.9,
            roughness: 0.1,
            clearcoat: 1,
            clearcoatRoughness: 0.05,
            transparent: true,
            opacity: 0.95
        });
        var core = new THREE.Mesh(coreGeo, coreMat);
        core.position.set(0, -3.5, 0);
        core.castShadow = true;
        scene.add(core);

        // ============================================================
        // ORBIT RINGS — Glowing wireframe rings
        // ============================================================
        var ringGeo = new THREE.TorusGeometry(9.5, 0.12, 8, 100);
        var ringMat = new THREE.MeshBasicMaterial({
            color: 0xa29bfe,
            wireframe: true,
            transparent: true,
            opacity: 0.4,
            blending: THREE.AdditiveBlending
        });
        var ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = Math.PI / 2.3;
        ring.rotation.z = Math.PI / 3.2;
        scene.add(ring);

        var ring2Geo = new THREE.TorusGeometry(12.5, 0.08, 8, 100);
        var ring2Mat = new THREE.MeshBasicMaterial({
            color: 0x74b9ff,
            wireframe: true,
            transparent: true,
            opacity: 0.2,
            blending: THREE.AdditiveBlending
        });
        var ring2 = new THREE.Mesh(ring2Geo, ring2Mat);
        ring2.rotation.x = Math.PI / 1.8;
        ring2.rotation.z = -Math.PI / 4;
        scene.add(ring2);

        // Third ring - thin glowing wireframe
        var ring3Geo = new THREE.TorusGeometry(7.5, 0.05, 8, 80);
        var ring3Mat = new THREE.MeshBasicMaterial({
            color: 0xa29bfe,
            wireframe: true,
            transparent: true,
            opacity: 0.35,
            blending: THREE.AdditiveBlending
        });
        var ring3 = new THREE.Mesh(ring3Geo, ring3Mat);
        ring3.rotation.x = Math.PI / 1.5;
        ring3.rotation.z = Math.PI / 5;
        scene.add(ring3);

        // ============================================================
        // FLOATING GEOMETRIC SHAPES — For depth and interest
        // ============================================================
        var floatShapes = [];
        var shapeTypes = [
            THREE.TetrahedronGeometry,
            THREE.OctahedronGeometry,
            THREE.IcosahedronGeometry,
            THREE.DodecahedronGeometry
        ];

        for (var f = 0; f < (isMobile ? 4 : 8); f++) {
            var shapeType = shapeTypes[Math.floor(Math.random() * shapeTypes.length)];
            var shapeGeo = new shapeType(1.5 + Math.random() * 2, 0);
            var shapeMat = new THREE.MeshPhysicalMaterial({
                color: 0x6c5ce7,
                emissive: 0x74b9ff,
                emissiveIntensity: 0.3 + Math.random() * 0.4,
                metalness: 0.7,
                roughness: 0.3,
                clearcoat: 0.8,
                clearcoatRoughness: 0.2,
                transparent: true,
                opacity: 0.7
            });
            var shape = new THREE.Mesh(shapeGeo, shapeMat);
            shape.position.set(
                (Math.random() - 0.5) * 30,
                (Math.random() - 0.5) * 20,
                (Math.random() - 0.5) * 15
            );
            shape.rotation.set(
                Math.random() * Math.PI,
                Math.random() * Math.PI,
                Math.random() * Math.PI
            );
            shape.castShadow = true;
            shape.receiveShadow = true;
            scene.add(shape);
            floatShapes.push({
                mesh: shape,
                speed: 0.002 + Math.random() * 0.004,
                bobSpeed: 0.5 + Math.random() * 1.0,
                bobAmp: 0.5 + Math.random() * 1.5
            });
        }

        // ============================================================
        // SPARKLE DUST — Small glowing particles
        // ============================================================
        var sparkCount = isMobile ? 30 : 100;
        var sparkGeom = new THREE.BufferGeometry();
        var sparkPos = new Float32Array(sparkCount * 3);
        for (var s = 0; s < sparkCount; s++) {
            sparkPos[s * 3] = (Math.random() - 0.5) * 80;
            sparkPos[s * 3 + 1] = (Math.random() - 0.5) * 50;
            sparkPos[s * 3 + 2] = (Math.random() - 0.5) * 30;
        }
        sparkGeom.setAttribute('position', new THREE.BufferAttribute(sparkPos, 3));
        var sparkMat = new THREE.PointsMaterial({
            color: 0x74b9ff,
            size: 0.4,
            transparent: true,
            opacity: 0.6,
            depthWrite: false,
            blending: THREE.AdditiveBlending
        });
        var sparks = new THREE.Points(sparkGeom, sparkMat);
        scene.add(sparks);

        // ============================================================
        // MOUSE + SCROLL TRACKING
        // ============================================================
        var mouse = { x: 0, y: 0 };
        var targetMouse = { x: 0, y: 0 };
        var scrollFactor = 0;

        document.addEventListener('mousemove', function (e) {
            targetMouse.x = (e.clientX / window.innerWidth) * 2 - 1;
            targetMouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
        }, false);

        window.addEventListener('scroll', function () {
            scrollFactor = window.scrollY / (window.innerHeight || 1);
        }, { passive: true });

        // ============================================================
        // ANIMATION LOOP
        // ============================================================
        var clock = new THREE.Clock();

        function animate() {
            requestAnimationFrame(animate);
            measureFPS();

            var elapsed = clock.getElapsedTime();

            // Smooth mouse easing
            mouse.x += (targetMouse.x - mouse.x) * 0.04;
            mouse.y += (targetMouse.y - mouse.y) * 0.04;

            // Particles drift upward with slight horizontal sway
            var posAttr = particleGeom.attributes.position;
            var arr = posAttr.array;
            for (var p = 0; p < particleCount; p++) {
                arr[p * 3 + 1] += speeds[p] * 0.02;
                arr[p * 3] += Math.sin(elapsed * 0.5 + p) * 0.001;
                if (arr[p * 3 + 1] > 120) arr[p * 3 + 1] = -120;
            }
            posAttr.needsUpdate = true;

            // Crystal bob + rotation
            crystal.position.y = -3.5 + Math.sin(elapsed * 0.9) * 1.4;
            crystal.rotation.y += 0.004;
            crystal.rotation.z += 0.0015;

            // Inner core pulses
            core.position.y = crystal.position.y;
            core.rotation.y += 0.006;
            core.rotation.z += 0.003;
            var coreScale = 1.0 + Math.sin(elapsed * 1.5) * 0.15;
            core.scale.set(coreScale, coreScale, coreScale);

            // Rings rotate
            ring.rotation.z += 0.0018;
            ring2.rotation.z -= 0.0012;
            ring3.rotation.z += 0.0025;

            // Floating shapes bob and rotate
            for (var fi = 0; fi < floatShapes.length; fi++) {
                var fObj = floatShapes[fi];
                fObj.mesh.rotation.y += fObj.speed;
                fObj.mesh.rotation.x += fObj.speed * 0.5;
                fObj.mesh.position.y += Math.sin(elapsed * fObj.bobSpeed) * fObj.bobAmp * 0.01;
            }

            // Camera subtle parallax with mouse
            camera.position.x += (mouse.x * 4 - camera.position.x) * 0.02;
            camera.position.y += (mouse.y * 3 - camera.position.y) * 0.02;
            camera.lookAt(0, 0, 0);

            // Scroll rotates the whole scene subtly
            scene.rotation.x = scrollFactor * 0.08;
            scene.rotation.y = mouse.x * 0.1;

            renderer.render(scene, camera);
        }
        animate();

        // --- Resize handling ---
        window.addEventListener('resize', function () {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        });

        // --- Style the canvas: fixed layer above body bg, behind content ---
        canvas.style.position = 'fixed';
        canvas.style.top = '0';
        canvas.style.left = '0';
        canvas.style.width = '100%';
        canvas.style.height = '100%';
        canvas.style.zIndex = '0';
        canvas.style.pointerEvents = 'none';
        canvas.style.opacity = '0.85';
        canvas.style.transition = 'opacity 0.6s ease';
    });
})();