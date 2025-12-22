let challengeChart = null;

function destroyChallenge() {
    if (challengeChart) { challengeChart.destroy(); challengeChart=null; }
    document.getElementById("challengeContainer").innerHTML="";
}

function renderChallenge(athletesData, monthIndex){
    const container = document.getElementById("challengeContainer");
    container.innerHTML=`<canvas id="challengeChartCanvas"></canvas>`;

    const canvas = document.getElementById("challengeChartCanvas");
    canvas.style.width="100%";
    canvas.style.height = window.innerWidth<=600?"250px":"400px";

    const datasets = Object.values(athletesData).map(a=>{
        let cumulative=0;
        const data=(a.daily_distance_km[monthIndex]||[]).map(d=>(cumulative+=d*0.621371).toFixed(2));
        return { label:a.display_name, data, borderColor:`hsl(${Math.random()*360},70%,60%)`, fill:false, tension:0.3, pointRadius:3, borderWidth:2 };
    });

    const labels = datasets[0]?.data.map((_,i)=>i+1)||[];
    const maxDistance = Math.max(...datasets.flatMap(d=>d.data),10);

    challengeChart = new Chart(canvas.getContext("2d"),{
        type:"line",
        data:{ labels, datasets },
        options:{ responsive:true, maintainAspectRatio:false, animation:false, plugins:{ legend:{ display:true, position:"bottom" } },
                  scales:{ x:{ title:{ display:true, text:"Day of Month" } }, y:{ min:0, max:maxDistance+5, title:{ display:true, text:"Cumulative Distance (mi)" } } } },
        plugins:[{
            id:"athleteImages",
            afterDatasetsDraw(chart){
                const { ctx, scales:{ x,y } } = chart;
                Object.values(athletesData).forEach((a,i)=>{
                    const dataset=chart.data.datasets[i]; if(!dataset.data.length) return;
                    const lastIndex=dataset.data.length-1;
                    const xPos=x.getPixelForValue(lastIndex+1);
                    const yPos=y.getPixelForValue(dataset.data[lastIndex]);
                    const img=new Image();
                    img.src=a.profile;
                    img.onload=()=>{ const size=window.innerWidth<=600?16:24; ctx.drawImage(img,xPos-size/2,yPos-size/2,size,size); };
                });
            }
        }]
    });
}

document.addEventListener("DOMContentLoaded",()=>{
    const toggle=document.getElementById("challengeToggle");
    toggle.addEventListener("change",()=>{
        const container=document.getElementById("container");
        const challengeContainer=document.getElementById("challengeContainer");
        const on=toggle.checked;

        container.style.display=on?"none":"flex";
        challengeContainer.style.display=on?"block":"none";

        if(on){
            window.DASHBOARD.destroyCharts();
            const { athletesData } = window.DASHBOARD.getData();
            const currentMonthIndex = new Date().getMonth();
            renderChallenge(athletesData,currentMonthIndex);
        }else{
            destroyChallenge();
            window.DASHBOARD.renderDashboard();
        }
    });
});
