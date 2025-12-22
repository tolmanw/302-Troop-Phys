let challengeChart = null;

function destroyChallenge() {
    if (challengeChart) {
        challengeChart.destroy();
        challengeChart = null;
    }
    const container = document.getElementById("challengeContainer");
    container.innerHTML = "";
}

// Random color generator
function getRandomColor() {
    const r = Math.floor(Math.random() * 200 + 30);
    const g = Math.floor(Math.random() * 200 + 30);
    const b = Math.floor(Math.random() * 200 + 30);
    return `rgb(${r},${g},${b})`;
}

// Render cumulative line chart
function renderChallenge(athletesData, monthIdx) {
    const container = document.getElementById("challengeContainer");
    container.innerHTML = `
        <div class="card" style="
            width: 100%;
            max-width: 600px;
            margin: 0 auto 20px auto;
            padding: 15px;
            background: #1b1f25;
            border-radius: 12px;
        ">
            <h2 style="text-align:left; margin-bottom:10px; font-size:18px;">Monthly Challenge</h2>
            <canvas id="challenge"></canvas>
        </div>
    `;

    const canvas = document.getElementById("challenge");
    canvas.style.width = "100%";
    canvas.style.height = window.innerWidth <= 600 ? "250px" : "400px";

    const athletes = Object.entries(athletesData);

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

    const labels = datasets[0]?.data.map((_, i) => i + 1) || [];
    const maxDistance = Math.max(...datasets.flatMap(d => d.data)) || 10;

    const ctx = canvas.getContext("2d");

    challengeChart = new Chart(ctx, {
        type: "line",
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: { 
                legend: { display: true, position: "bottom" }
            },
            scales: {
                x: { title: { display: true, text: "Day of Month" } },
                y: { title: { display: true, text: "Cumulative Distance (mi)" }, min:0, max: maxDistance + 5 }
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

// Toggle listener
document.addEventListener
