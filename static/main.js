// static/main.js
const scene = new THREE.Scene();
const container = document.getElementById('container');

// Basic camera setup
const camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000);
camera.position.z = 2.5; // Start further back

// Renderer setup
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(container.clientWidth, container.clientHeight);
renderer.setPixelRatio(window.devicePixelRatio); // Adjust for high DPI screens
container.appendChild(renderer.domElement);

// OrbitControls for interaction (zoom, pan, rotate)
const controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.enableDamping = true; // Smooths camera movement
controls.dampingFactor = 0.05;
controls.minDistance = 1.5; // Don't zoom in too close
controls.maxDistance = 10;  // Don't zoom out too far

// Globe Setup
const globeRadius = 1;
const globeGeometry = new THREE.SphereGeometry(globeRadius, 64, 64); // More segments for smoother globe

// Texture Loader for Earth map
const textureLoader = new THREE.TextureLoader();
const earthTexture = textureLoader.load('static/earthmap.jpg'); // We'll need an earth map texture
const earthMaterial = new THREE.MeshBasicMaterial({ map: earthTexture });
const globe = new THREE.Mesh(globeGeometry, earthMaterial);
scene.add(globe);

// Lighting
const ambientLight = new THREE.AmbientLight(0xffffff, 0.7); // Soft white light
scene.add(ambientLight);
const directionalLight = new THREE.DirectionalLight(0xffffff, 0.5);
directionalLight.position.set(5, 3, 5);
scene.add(directionalLight);

// Group to hold the plotted points
const pointsGroup = new THREE.Group();
globe.add(pointsGroup); // Add points relative to the globe

// Store point meshes and their creation time
let plottedPoints = []; // { mesh: THREE.Mesh, timestamp: number }

// Function to convert Latitude/Longitude to Cartesian coordinates
function latLonToVector3(lat, lon, radius) {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lon + 180) * (Math.PI / 180);

    const x = -(radius * Math.sin(phi) * Math.cos(theta));
    const y = radius * Math.cos(phi);
    const z = radius * Math.sin(phi) * Math.sin(theta);

    return new THREE.Vector3(x, y, z);
}

// Function to create a point mesh
function createPoint(lat, lon, isSuspicious) {
    const pointRadius = 0.008; // Adjust size as needed
    const pointGeometry = new THREE.SphereGeometry(pointRadius, 8, 8);
    const pointColor = isSuspicious ? 0xff0000 : 0x00ff00; // Red for suspicious, Green for normal
    const pointMaterial = new THREE.MeshBasicMaterial({ color: pointColor });
    const pointMesh = new THREE.Mesh(pointGeometry, pointMaterial);

    // Position the point on the globe surface
    const position = latLonToVector3(lat, lon, globeRadius);
    pointMesh.position.copy(position);

    return pointMesh;
}

// Function to fetch data and update visualization
const FETCH_INTERVAL = 2000; // Fetch data every 2 seconds
const POINT_LIFESPAN_MS = 10000; // Remove points after 10 seconds

let lastProcessedIndex = -1; // Track the last index processed from the fetched data

// --- Chart.js Setup ---
const activityCtx = document.getElementById('activityChart').getContext('2d');
let activityChart = null; // Initialize chart variable

function initializeChart(initialData = []) {
    // Destroy previous chart instance if it exists
    if (activityChart) {
        activityChart.destroy();
    }

    const labels = initialData.map(d => new Date(d.timestamp * 1000)); // Convert Unix seconds to JS Date objects
    const dataPoints = initialData.map(d => d.count);

    activityChart = new Chart(activityCtx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Requests per Second',
                data: dataPoints,
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1,
                fill: false,
                pointRadius: 2 // Smaller points
            }]
        },
        options: {
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'second',
                        tooltipFormat: 'HH:mm:ss', // Format for tooltips
                        displayFormats: {
                            second: 'HH:mm:ss' // Format for axis labels
                        }
                    },
                    title: {
                        display: true,
                        text: 'Time'
                    },
                    ticks: {
                        maxRotation: 0, // Prevent label rotation
                        autoSkip: true, // Automatically skip labels to prevent overlap
                        maxTicksLimit: 6 // Limit number of visible time labels
                    }
                },
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Count'
                    },
                     // Suggest integer steps if max count is low
                    ticks: {
                        stepSize: 1, // Force integer steps if appropriate
                        precision: 0 // Ensure integer labels
                    }
                }
            },
            animation: {
                duration: 0 // Disable animation for real-time updates
            },
            plugins: {
                legend: {
                    display: false // Hide legend if only one dataset
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
             maintainAspectRatio: false // Allow chart to resize vertically
        }
    });
}
// --- End Chart.js Setup ---

async function fetchDataAndUpdate() {
    try {
        const response = await fetch('/get_traffic');
        if (!response.ok) {
            console.error('Failed to fetch traffic data:', response.statusText);
            return;
        }
        const data = await response.json();
        const newPoints = data.points;
        const activityData = data.activity; // Get activity data

        // --- Add new points (same logic as before) ---
        let addedCount = 0;
        for (let i = lastProcessedIndex + 1; i < newPoints.length; i++) {
             const pointData = newPoints[i];
             if (pointData) {
                const pointMesh = createPoint(pointData.lat, pointData.lon, pointData.suspicious === 1);
                pointsGroup.add(pointMesh);
                plottedPoints.push({ mesh: pointMesh, addedTime: Date.now() });
                addedCount++;
             }
        }
        if (addedCount > 0) {
            // console.log(`Added ${addedCount} new points.`); // Less verbose logging
            lastProcessedIndex = newPoints.length - 1;
        }
        // --- End new point addition ---


        // --- Update Info Panel ---
        // Top Countries - Updated Section
        const countriesList = document.getElementById('countries-list'); // Use new ID
        countriesList.innerHTML = ''; // Clear previous list
        if (data.top_countries && data.top_countries.length > 0) {
            data.top_countries.forEach(countryData => {
                const li = document.createElement('li');
                // Display Country Code (e.g., US, DE, CN) and count
                li.textContent = `${countryData.country || 'Unknown'}: ${countryData.count} hits`;
                countriesList.appendChild(li);
            });
        } else {
            const li = document.createElement('li');
            li.textContent = 'Waiting for data...';
            countriesList.appendChild(li);
        }

        // Stats (same logic as before)
        const totalPoints = plottedPoints.length;
        const suspiciousPoints = plottedPoints.filter(p => p.mesh.material.color.getHex() === 0xff0000).length;
        document.getElementById('points-count').textContent = totalPoints;
        document.getElementById('suspicious-count').textContent = suspiciousPoints;
        // --- End Info Panel Update ---


        // --- Update Activity Chart ---
        if (activityChart && activityData) {
             activityChart.data.labels = activityData.map(d => new Date(d.timestamp * 1000));
             activityChart.data.datasets[0].data = activityData.map(d => d.count);
             activityChart.update(); // Update the chart
        }
        // --- End Activity Chart Update ---


    } catch (error) {
        console.error('Error fetching or processing data:', error);
    }
}


// Animation Loop
function animate() {
    requestAnimationFrame(animate);

    // Update controls
    controls.update();

    // Remove old points
    const now = Date.now();
    const pointsToRemove = [];
    plottedPoints = plottedPoints.filter(p => {
        if (now - p.addedTime > POINT_LIFESPAN_MS) {
            pointsToRemove.push(p.mesh);
            return false; // Remove from plottedPoints array
        }
        return true; // Keep in plottedPoints array
    });

    pointsToRemove.forEach(mesh => {
        pointsGroup.remove(mesh);
        mesh.geometry.dispose(); // Clean up geometry
        mesh.material.dispose(); // Clean up material
    });


    renderer.render(scene, camera);
}

// Handle window resize
window.addEventListener('resize', () => {
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
}, false);

// Initial chart setup (can be empty or based on first fetch)
initializeChart();

// Initial fetch and start interval
fetchDataAndUpdate();
setInterval(fetchDataAndUpdate, FETCH_INTERVAL);

// Start animation
animate();

// Add a placeholder earthmap.jpg - you should replace this with a real one!
// For now, let's just log a message.
console.log("Remember to add an 'earthmap.jpg' file in the 'static' directory!"); 