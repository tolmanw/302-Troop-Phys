let challengeChart = null;

async function loadChallengeData() {
    const response = await fetch("data/athletes.json");
    return await response.json();
}

function getLastMonthWithData(athletesData) {
    const numMonths = Object.values(athletesData)[0].daily_distance_km.length;
    for (let i = numMonths - 1; i >= 0; i--) {
        if (Object.values(athletesData).some(a => (a.daily_distance_km[i] || []).some(d => d > 0))) {
            return i;
        }
    }
    return numMonths - 1;
}

function destroyChallenge() {
    if (challengeChart) {
        challengeChart.destroy();
        challengeChart = null;
    }
    const container = document.getElementById("challengeContainer");
    container.innerHTML = `
        <h2 style="text-align:left; margin-bottom:10px;">Monthly Challenge</h2>
        <canvas id="challenge"></canvas>`;
}

function renderChallenge(athletesData, monthIdx) {
    const canvas = document.getElementById("challenge");
    if (!canvas) return;

    canvas.style.width = "100%";
    canvas.style.height = window.innerWidth <= 600 ? "250px" : "400px";

    const athletes = Object.entries(athletesData);

    const datasets = athletes.map(([alias, a]) => {
        let cumulative = 0;
        const data = (a.daily_distance_km[monthIdx] || []).map(d => +(cumulative += d * 0.621371).toFixed(2));
        return {
            label: a.display_name,
            data,
            tension: 0.3,
            borderColor: getRandomColor(),
            fill: false,
            pointRadius: 3,
            borderWidth: 2
        };
    });

    const labels = datasets[0]?.data.map((_, i) => i + 1) || [];
    const ctx = canvas.getContext("2d");

    challengeChart = new Chart(ctx, {
        type: "line",
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: { legend: { display: true, position: "bottom" } },
            layout: { padding: { left: 10, right: 10, top: 10, bottom: 10 } },
            scales: {
                x: { title: { display: true, text: "Day of Month" } },
                y: { title: { display: true, text: "Cumulative Distance (mi)" }, beginAtZero: true }
            }
        },
        plugins: [{
            id: "athleteImages",
            afterDatasetsDraw(chart) {
                const { ctx, scales: { x, y } } = chart;
                athletes.forEach(([alias, a], i) => {
                    const dataset = chart.data.datasets[i];
                    if (!dataset.data.length) return;
                    const lastIndex = dataset.data.length - 1;
                    const xPos = x.getPixelForValue(lastIndex + 1);
                    const yPos = y.getPixelForValue(dataset.data[lastIndex]);

                    const img = new Image();
                    img.src = a.profile;
                    img.onload = () => {
                        const size = window.innerWidth <= 600 ? 16 : 24;
                        ctx.drawImage(img, xPos - size / 2, yPos - size / 2, size, size);
                    };
                });
            }
        }]
    });
}

function getRandomColor() {
    const r = Math.floor(Math.random() * 200 + 30);
    const g = Math.floor(Math.random() * 200 + 30);
    const b = Math.floor(Math.random() * 200 + 30);
    return `rgb(${r},${g},${b})`;
}

// --- Toggle listener ---
document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.getElementById("challengeToggle");
    toggle.addEventListener("change", async e => {
        const on = e.target.checked;
        const container = document.getElementById("challengeContainer");
        document.getElementById("container").style.display = on ? "none" : "flex";
        container
