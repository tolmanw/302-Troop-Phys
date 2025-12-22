let challengeChart = null;

// Load JSON data
async function loadChallengeData() {
    const response = await fetch("data/athletes.json");
    return await response.json();
}

// Toggle listener
document.getElementById("challengeToggle").addEventListener("change", async e => {
    const on = e.target.checked;
    const container = document.getElementById("challengeContainer");
    document.getElementById("container").style.display = on ? "none" : "flex";
    container.style.display = on ? "block" : "none";

    if (on) {
        destroyChallenge();
        const data = await loadChallengeData();
        const currentMonthIndex = new Date().getMonth();
        renderChallenge(data.athletes, data.month_names, currentMonthIndex);
    } else {
        destroyChallenge();
        document.getElementById("container").style.display = "flex";
    }
});

// Destroy previous chart
function destroyChallenge() {
    if (challengeChart) {
        challengeChart.destroy();
        challengeChart = null;
    }
    const container = document.getElementById("challengeContainer");
    container.innerHTML = `
        <div class="daily-chart-wrapper chart-tile">
            <h3 style="text-align:center;"></h3>
            <canvas id="challenge"></canvas>
        </div>`;
}

// Render cumulative distance chart
function renderChallenge(athletesData, monthNames, monthIdx) {
    const container = document.getElementById("challengeContainer");
    const wrapper = container.querySelector(".daily-chart-wrapper");
    wrapper.querySelector("h3").textContent = `${monthNames[monthIdx]} Challenge`;

    // Set fixed wrapper height like dashboard
    const dailyWidth = window.innerWidth <= 600 ? wrapper.clientWidth : 305;
    const dailyHeight = window.innerWidth <= 600 ? 200 : 170;
    wrapper.style.width = dailyWidth + "px";
    wrapper.style.height = dailyHeight + "px";

    const athletes = Object.entries(athletesData); // [alias, athlete]

    // cumulative distances
    const datasets = athletes.map(([alias, a]) => {
        let cumulative = 0;
        const data = (a.daily_distance_km[monthIdx] || []).map(d => +(cumulative += d*0.621371).toFixed(2));
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

    const labels = datasets[0]?.data.map((_, i) => i+1) || [];

    const canvas = wrapper.querySelector("#challenge");
    canvas.style.width = "100%";
    canvas.style.height = "100%";

    challengeChart = new Chart(canvas, {
        type: "line",
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: { legend: { display: true, position: "bottom" } },
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
                        ctx.drawImage(img, xPos - size/2, yPos - size/2, size, size);
                    };
                });
            }
        }]
    });
}

function getRandomColor() {
    const r = Math.floor(Math.random()*200+30);
    const g = Math.floor(Math.random()*200+30);
    const b = Math.floor(Math.random()*200+30);
    return `rgb(${r},${g},${b})`;
}
