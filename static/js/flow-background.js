const canvas = document.getElementById("flow-background");

if (canvas) {
    import("https://unpkg.com/three@0.165.0/build/three.module.js")
        .then((module) => runThreeFlow(module))
        .catch(() => runCanvasFallback());
}

function runThreeFlow(THREE) {
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(58, window.innerWidth / window.innerHeight, 0.1, 120);
    const renderer = new THREE.WebGLRenderer({
        canvas,
        alpha: true,
        antialias: true,
        powerPreference: "high-performance",
    });

    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    camera.position.set(0, 0, 28);

    const group = new THREE.Group();
    scene.add(group);

    const particleCount = 160;
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);
    const palette = [
        new THREE.Color("#40e0c2"),
        new THREE.Color("#f7c948"),
        new THREE.Color("#7dd3fc"),
        new THREE.Color("#f472b6"),
    ];

    for (let index = 0; index < particleCount; index += 1) {
        const i = index * 3;
        const lane = (index % 8) - 3.5;
        positions[i] = lane * 3.2 + (Math.random() - 0.5) * 1.4;
        positions[i + 1] = (Math.random() - 0.5) * 24;
        positions[i + 2] = (Math.random() - 0.5) * 22;

        const color = palette[index % palette.length];
        colors[i] = color.r;
        colors[i + 1] = color.g;
        colors[i + 2] = color.b;
    }

    const particleGeometry = new THREE.BufferGeometry();
    particleGeometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    particleGeometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));

    const particleMaterial = new THREE.PointsMaterial({
        size: 0.16,
        transparent: true,
        opacity: 0.78,
        vertexColors: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
    });

    group.add(new THREE.Points(particleGeometry, particleMaterial));

    const linePositions = [];
    for (let lane = -4; lane <= 4; lane += 1) {
        for (let step = -8; step < 8; step += 1) {
            linePositions.push(lane * 3, step * 1.7, -8 + Math.sin(step * 0.6) * 3);
            linePositions.push(lane * 3, (step + 1) * 1.7, -8 + Math.sin((step + 1) * 0.6) * 3);
        }
    }

    const lineGeometry = new THREE.BufferGeometry();
    lineGeometry.setAttribute("position", new THREE.Float32BufferAttribute(linePositions, 3));
    const dataLanes = new THREE.LineSegments(
        lineGeometry,
        new THREE.LineBasicMaterial({
            color: "#38bdf8",
            transparent: true,
            opacity: 0.16,
            blending: THREE.AdditiveBlending,
        })
    );
    group.add(dataLanes);

    const ringGeometry = new THREE.TorusGeometry(6.8, 0.018, 8, 120);
    const ringMaterial = new THREE.MeshBasicMaterial({
        color: "#f7c948",
        transparent: true,
        opacity: 0.18,
    });

    const rings = [];
    for (let index = 0; index < 3; index += 1) {
        const ring = new THREE.Mesh(ringGeometry, ringMaterial.clone());
        ring.rotation.x = Math.PI / 2.8;
        ring.rotation.y = index * 0.65;
        ring.position.x = index === 1 ? 7 : -7;
        ring.position.y = index === 2 ? -4 : 4;
        ring.position.z = -10 - index * 2;
        ring.material.opacity = 0.12 + index * 0.04;
        group.add(ring);
        rings.push(ring);
    }

    const clock = new THREE.Clock();

    function resize() {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    }

    function animate() {
        const elapsed = clock.getElapsedTime();
        const positionAttribute = particleGeometry.getAttribute("position");

        for (let index = 0; index < particleCount; index += 1) {
            const yIndex = index * 3 + 1;
            const zIndex = index * 3 + 2;
            positions[yIndex] += 0.018 + (index % 5) * 0.002;
            positions[zIndex] += Math.sin(elapsed + index) * 0.002;

            if (positions[yIndex] > 13) {
                positions[yIndex] = -13;
            }
        }

        positionAttribute.needsUpdate = true;
        group.rotation.y = Math.sin(elapsed * 0.18) * 0.22;
        group.rotation.x = Math.cos(elapsed * 0.12) * 0.08;
        dataLanes.position.y = Math.sin(elapsed * 0.4) * 0.8;

        rings.forEach((ring, index) => {
            ring.rotation.z = elapsed * (0.15 + index * 0.05);
            ring.scale.setScalar(1 + Math.sin(elapsed * 0.6 + index) * 0.05);
        });

        renderer.render(scene, camera);
        requestAnimationFrame(animate);
    }

    window.addEventListener("resize", resize);
    animate();
}

function runCanvasFallback() {
    const context = canvas.getContext("2d");
    const particles = Array.from({ length: 90 }, (_, index) => ({
        x: Math.random(),
        y: Math.random(),
        z: 0.4 + Math.random() * 1.8,
        lane: index % 7,
        color: ["#40e0c2", "#f7c948", "#7dd3fc", "#f472b6"][index % 4],
    }));

    function resize() {
        const ratio = Math.min(window.devicePixelRatio || 1, 2);
        canvas.width = window.innerWidth * ratio;
        canvas.height = window.innerHeight * ratio;
        canvas.style.width = `${window.innerWidth}px`;
        canvas.style.height = `${window.innerHeight}px`;
        context.setTransform(ratio, 0, 0, ratio, 0, 0);
    }

    function animate() {
        context.clearRect(0, 0, window.innerWidth, window.innerHeight);
        context.globalCompositeOperation = "lighter";

        particles.forEach((particle) => {
            particle.y -= 0.0018 * particle.z;
            if (particle.y < -0.05) {
                particle.y = 1.05;
            }

            const perspective = 0.45 + particle.z * 0.28;
            const x = window.innerWidth * (0.18 + particle.lane * 0.105 + Math.sin(Date.now() * 0.0008 + particle.z) * 0.02);
            const y = window.innerHeight * particle.y;
            const radius = 1.6 + particle.z * 1.2;

            context.beginPath();
            context.fillStyle = particle.color;
            context.globalAlpha = 0.32 * perspective;
            context.arc(x, y, radius, 0, Math.PI * 2);
            context.fill();

            context.beginPath();
            context.strokeStyle = particle.color;
            context.globalAlpha = 0.08 * perspective;
            context.moveTo(x, y);
            context.lineTo(x + Math.sin(particle.z * 4) * 38, y + 92 * perspective);
            context.stroke();
        });

        context.globalCompositeOperation = "source-over";
        requestAnimationFrame(animate);
    }

    window.addEventListener("resize", resize);
    resize();
    animate();
}
