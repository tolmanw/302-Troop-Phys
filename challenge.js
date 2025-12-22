export const lineEndImagePlugin = {
    id: 'lineEndImage',
    afterDatasetsDraw(chart){
        const {ctx} = chart;
        chart.data.datasets.forEach((ds,index)=>{
            const meta = chart.getDatasetMeta(index);
            if(!meta.hidden && meta.data.length){
                const pt = meta.data[meta.data.length-1];
                const img = ds._profileImage;
                if(!img) return;
                const size=26;
                ctx.save();
                ctx.beginPath();
                ctx.arc(pt.x, pt.y, size/2, 0, Math.PI*2);
                ctx.clip();
                ctx.drawImage(img, pt.x-size/2, pt.y-size/2, size, size);
                ctx.restore();
            }
        });
    }
};

export function cumulativeMilesForMonth(athlete, monthIndex){
    let total=0;
    return athlete.daily_distance_km[monthIndex].map(d=>{ total+=d*0.621371; return +total.toFixed(2); });
}

export function renderChallengeView(athletesData, monthNames, monthIndex, CHARTS){
    const container=document.getElementById("challengeContainer");
    container.innerHTML="";

    const firstAthlete=Object.values(athletesData)[0];
    const daysInMonth=firstAthlete.daily_distance_km[monthIndex].length;
    const labels=Array.from({length:daysInMonth},(_,i)=>i+1);

    const datasets=[];
    const imageLoads=[];
    const leaderboard=[];

    Object.values(athletesData).forEach((athlete)=>{
        const img=new Image();
        img.src=athlete.profile;
        imageLoads.push(new Promise(r=>img.onload=r));
        const cumulative=cumulativeMilesForMonth(athlete,monthIndex);
        datasets.push({ label:athlete.display_name, data:cumulative, borderWidth:2, tension:0.35, pointRadius:0, fill:false, _profileImage:img });
        leaderboard.push({name:athlete.display_name,total:cumulative[cumulative.length-1],img:athlete.profile});
    });

    leaderboard.sort((a,b)=>b.total-a.total);
    const top3=leaderboard.slice(0,3);

    const card=document.createElement("div");
    card.className="card";
    card.style.width="100%";
    card.innerHTML=`
        <h2 style="text-align:center;margin-bottom:10px;">Monthly Distance Challenge – ${monthNames[monthIndex]}</h2>
        <div class="daily-chart-wrapper chart-tile" style="height:420px;">
            <canvas id="challengeLineChart"></canvas>
        </div>
        <div style="margin-top:15px;">
            <h3 style="text-align:center;">Leaderboard</h3>
            <ol id="challengeLeaderboard"></ol>
        </div>`;
    container.appendChild(card);

    const leaderboardEl=document.getElementById("challengeLeaderboard");
    leaderboardEl.innerHTML=top3.map(p=>`<li><img src="${p.img}" style="width:24px;height:24px;border-radius:50%;margin-right:5px;">${p.name}: ${p.total} mi</li>`).join('');

    Promise.all(imageLoads).then(()=>{
        if(CHARTS.challengeLine){CHARTS.challengeLine.destroy();delete CHARTS.challengeLine;}
        CHARTS.challengeLine=new Chart(document.getElementById("challengeLineChart"),{
            type:"line",
            data:{labels,datasets},
            options:{responsive:true, maintainAspectRatio:false, animation:{duration:1500}, plugins:{legend:{position:"bottom"}}, scales:{x:{title:{display:true,text:"Day"}}, y:{beginAtZero:true,title:{display:true,text:"Miles"}}}},
            plugins:[lineEndImagePlugin]
        });
    });
}
