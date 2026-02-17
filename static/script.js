document.addEventListener("DOMContentLoaded", function () {

let fsiChart = null;
let simulationChart = null;
let riskDriverChart = null;
let baselineScore = null;

/* ================= SIDEBAR ACTIVE ================= */
document.querySelectorAll(".sidebar li").forEach(item => {
    item.addEventListener("click", function(){
        document.querySelectorAll(".sidebar li")
            .forEach(i => i.classList.remove("active"));
        this.classList.add("active");
    });
});

/* ================= TAB SWITCHING ================= */
window.showDashboard = function () {
    document.getElementById("dashboardContent").classList.remove("hidden");
    document.getElementById("simulationSection").classList.add("hidden");
    document.getElementById("alertsSection").classList.add("hidden");
    document.getElementById("aiHelpSection").classList.add("hidden");
};

window.showSimulation = function () {
    document.getElementById("dashboardContent").classList.add("hidden");
    document.getElementById("simulationSection").classList.remove("hidden");
    document.getElementById("alertsSection").classList.add("hidden");
    document.getElementById("aiHelpSection").classList.add("hidden");
};

window.showAlerts = function () {
    document.getElementById("dashboardContent").classList.add("hidden");
    document.getElementById("simulationSection").classList.add("hidden");
    document.getElementById("alertsSection").classList.remove("hidden");
    document.getElementById("aiHelpSection").classList.add("hidden");
};

window.showAIHelp = function () {
    document.getElementById("dashboardContent").classList.add("hidden");
    document.getElementById("simulationSection").classList.add("hidden");
    document.getElementById("alertsSection").classList.add("hidden");
    document.getElementById("aiHelpSection").classList.remove("hidden");
};

window.toggleAdvanced = function () {
    document.getElementById("advancedSection").classList.toggle("hidden");
};

/* ================= SLIDER LIVE UPDATE ================= */
["rain","cost","market"].forEach(type => {

    const slider = document.getElementById(type + "Slider");
    const label = document.getElementById(type + "Val");

    function updateSlider() {
        label.innerText = slider.value + "%";
        const percent = ((slider.value - slider.min) / (slider.max - slider.min)) * 100;

        slider.style.background =
            `linear-gradient(to right,
            #1f7a4c 0%,
            #1f7a4c ${percent}%,
            #e5e7eb ${percent}%,
            #e5e7eb 100%)`;
    }

    slider.addEventListener("input", updateSlider);
    updateSlider();
});

/* ================= MAIN GAUGE ================= */
function updateGauge(score, level) {

    let color = "#2e7d32";
    if (level === "MODERATE") color = "#f4b400";
    if (level === "HIGH") color = "#d32f2f";

    if (fsiChart) fsiChart.destroy();

    fsiChart = new Chart(document.getElementById("fsiGauge"), {
        type: "doughnut",
        data: {
            datasets: [{
                data: [score, 100-score],
                backgroundColor: [color, "#e0e0e0"],
                borderWidth: 0
            }]
        },
        options: {
            cutout: "80%",
            animation: { duration: 1200 },
            plugins:{ legend:{ display:false }}
        }
    });

    document.getElementById("gaugeValue").innerText = Math.round(score);
    document.getElementById("gaugeLabel").innerText = level + " RISK";
}

/* ================= RISK DRIVER CHART ================= */
function updateRiskDrivers(breakdown) {

    if (!breakdown) return;

    const sorted = Object.entries(breakdown)
        .sort((a,b)=>b[1]-a[1])
        .slice(0,3);

    if (riskDriverChart) riskDriverChart.destroy();

    riskDriverChart = new Chart(document.getElementById("riskDriverChart"), {
        type: "bar",
        data: {
            labels: sorted.map(x=>x[0].toUpperCase()),
            datasets: [{
                data: sorted.map(x=>x[1]),
                backgroundColor: ["#d32f2f","#f4b400","#2e7d32"]
            }]
        },
        options: {
            indexAxis: "y",
            animation: { duration: 1000 },
            plugins:{ legend:{ display:false }},
            scales:{ x:{ beginAtZero:true, max:100 }}
        }
    });

    document.getElementById("riskDriverSection").classList.remove("hidden");
}

/* ================= FORM SUBMIT ================= */
document.getElementById("riskForm").addEventListener("submit", async function(e){

    e.preventDefault();

    const data = Object.fromEntries(new FormData(this).entries());

    const response = await fetch("/predict",{
        method:"POST",
        headers:{ "Content-Type":"application/json" },
        body:JSON.stringify(data)
    });

    const result = await response.json();
    if(result.error) return;

    document.getElementById("result").classList.remove("hidden");

    updateGauge(result.risk_score,result.risk_level);
    updateRiskDrivers(result.breakdown);
    document.getElementById("riskSummary").innerText = result.summary;

    handleAlerts(result.alerts);
    renderAIHelp(result.recommendations);

    baselineScore = result.risk_score;
});

/* ================= SIMULATION ================= */
window.runSimulation = async function(){

    if (baselineScore === null) {
        alert("Please calculate baseline first.");
        return;
    }

    const data = Object.fromEntries(
        new FormData(document.getElementById("riskForm")).entries()
    );

    data.Rainfall_Deviation = document.getElementById("rainSlider").value;
    data.Market_Volatility = document.getElementById("marketSlider").value/100;
    data.Input_Cost = parseFloat(data.Input_Cost) *
        (1 + document.getElementById("costSlider").value/100);

    const response = await fetch("/predict",{
        method:"POST",
        headers:{ "Content-Type":"application/json" },
        body:JSON.stringify(data)
    });

    const result = await response.json();
    const newScore = result.risk_score;
    const delta = newScore - baselineScore;

    let color = "#2e7d32";
    if(newScore >= 40) color = "#f4b400";
    if(newScore > 70) color = "#d32f2f";

    if(simulationChart) simulationChart.destroy();

    const centerTextPlugin = {
        id: "centerText",
        beforeDraw(chart) {
            const { width, height, ctx } = chart;
            ctx.save();
            ctx.font = "bold " + (height / 4.5) + "px Segoe UI";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillStyle = color;
            ctx.fillText(Math.round(newScore) + "%", width / 2, height / 2);
            ctx.restore();
        }
    };

    simulationChart = new Chart(document.getElementById("simulationGauge"), {
        type: "doughnut",
        data: {
            datasets: [{
                data: [newScore,100-newScore],
                backgroundColor:[color,"#e0e0e0"],
                borderWidth:0
            }]
        },
        options:{
            cutout:"80%",
            animation:{ duration:1200 },
            plugins:{ legend:{ display:false }}
        },
        plugins: [centerTextPlugin]
    });

    document.getElementById("simDelta").innerHTML =
        `Baseline: ${baselineScore.toFixed(1)}% → Now: ${newScore.toFixed(1)}%<br>
         Change: ${delta > 0 ? "+" : ""}${delta.toFixed(1)}%`;

    document.getElementById("simInsight").innerText =
        delta > 5 ? "Scenario significantly increases instability."
        : delta < -5 ? "Scenario significantly improves resilience."
        : "Minimal impact detected.";
};

/* ================= AI HELP ================= */
function renderAIHelp(recommendations) {

    const list = document.getElementById("aiHelpList");
    const badge = document.getElementById("aiBadge");

    if (!list) return;

    list.innerHTML = "";

    if (!recommendations || recommendations.length === 0) {
        list.innerHTML = "<li>No strategic recommendations at this time.</li>";
        badge.classList.add("hidden");
        return;
    }

    recommendations.forEach(rec => {
        const li = document.createElement("li");
        li.style.marginBottom = "12px";
        li.innerHTML = "✔ " + rec;
        list.appendChild(li);
    });

    badge.classList.remove("hidden");
}

/* ================= PROFESSIONAL ALERT SYSTEM ================= */
function handleAlerts(alertsData) {

    const alertCard = document.getElementById("alertCard");
    const popupContainer = document.getElementById("alertPopupContainer");
    const badge = document.getElementById("alertBadge");

    alertCard.classList.remove("hidden");
    alertCard.innerHTML = "";
    popupContainer.innerHTML = "";

    if (!alertsData || alertsData.length === 0) {
        badge.classList.add("hidden");
        alertCard.innerHTML = `
            <h3>✅ Stable Condition</h3>
            <p>No significant risk alerts detected.</p>
        `;
        return;
    }

    badge.classList.remove("hidden");
    badge.innerText = alertsData.length;

    alertsData.forEach(alert => {

        let borderColor = "#2e7d32";
        let popupClass = "alert-info";

        if (alert.type === "critical") {
            borderColor = "#d32f2f";
            popupClass = "alert-critical";
        }

        if (alert.type === "warning") {
            borderColor = "#f4b400";
            popupClass = "alert-warning";
        }

        /* ===== Alerts Tab Cards ===== */
        const card = document.createElement("div");
        card.style.borderLeft = "6px solid " + borderColor;
        card.style.padding = "15px";
        card.style.marginBottom = "15px";
        card.style.background = "#fff";
        card.style.borderRadius = "10px";
        card.style.boxShadow = "0 6px 20px rgba(0,0,0,0.05)";
        card.innerHTML = `
            <h3>${alert.title}</h3>
            <p>${alert.message}</p>
        `;
        alertCard.appendChild(card);

        /* ===== Floating Popup ===== */
        const popup = document.createElement("div");
        popup.className = "alert-popup " + popupClass;
        popup.innerHTML = `
            <h4>${alert.title}</h4>
            <p>${alert.message}</p>
        `;

        popup.onclick = function() {
            showAlerts();
            popup.remove();
        };

        popupContainer.appendChild(popup);

        if (alert.type !== "critical") {
            setTimeout(() => popup.remove(), 5000);
        }
    });
}

});
