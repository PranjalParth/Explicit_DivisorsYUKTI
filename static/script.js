document.addEventListener("DOMContentLoaded", function () {

let fsiChart = null;
let simulationChart = null;
let riskDriverChart = null;

/* ================= TAB SWITCHING ================= */

window.showSimulation = function () {
    document.getElementById("dashboardContent").classList.add("hidden");
    document.getElementById("simulationSection").classList.remove("hidden");
};

window.showDashboard = function () {
    document.getElementById("simulationSection").classList.add("hidden");
    document.getElementById("dashboardContent").classList.remove("hidden");
};

/* ================= ADVANCED TOGGLE ================= */

window.toggleAdvanced = function () {
    document.getElementById("advancedSection").classList.toggle("hidden");
};

/* ================= ANIMATION ================= */

function animateNumber(id, value) {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerText = Math.round(value);
}

/* ================= GAUGE ================= */

function updateGauge(score, level) {

    const canvas = document.getElementById("fsiGauge");
    if (!canvas) return;

    let color = "#2e7d32";
    if (level === "MODERATE") color = "#f4b400";
    if (level === "HIGH") color = "#d32f2f";

    if (fsiChart) fsiChart.destroy();

    fsiChart = new Chart(canvas, {
        type: "doughnut",
        data: {
            datasets: [{
                data: [score, 100 - score],
                backgroundColor: [color, "#e0e0e0"],
                borderWidth: 0
            }]
        },
        options: {
            cutout: "80%",
            plugins: { legend: { display: false } }
        }
    });

    animateNumber("gaugeValue", score);
    document.getElementById("gaugeLabel").innerText = level + " RISK";
}

/* ================= RISK DRIVER CHART ================= */

function updateRiskDrivers(breakdown) {

    const section = document.getElementById("riskDriverSection");
    const canvas = document.getElementById("riskDriverChart");

    if (!breakdown || !canvas) return;

    const sorted = Object.entries(breakdown)
        .sort((a,b)=>b[1]-a[1])
        .slice(0,3);

    if (riskDriverChart) riskDriverChart.destroy();

    riskDriverChart = new Chart(canvas, {
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
            plugins: { legend: { display: false } },
            scales: { x: { max:100 } }
        }
    });

    section.classList.remove("hidden");
}

/* ================= FORM ================= */

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

});

/* ================= SIMULATION ================= */

window.runSimulation = async function(){

    const data = Object.fromEntries(
        new FormData(document.getElementById("riskForm")).entries()
    );

    data.Rainfall_Deviation = document.getElementById("rainSlider").value;
    data.Market_Volatility = document.getElementById("marketSlider").value/100;
    data.Input_Cost = data.Input_Cost *
        (1 + document.getElementById("costSlider").value/100);

    const response = await fetch("/predict",{
        method:"POST",
        headers:{ "Content-Type":"application/json" },
        body:JSON.stringify(data)
    });

    const result = await response.json();
    if(!result.risk_score) return;

    const canvas = document.getElementById("simulationGauge");

    if(simulationChart) simulationChart.destroy();

    simulationChart = new Chart(canvas,{
        type:"doughnut",
        data:{
            datasets:[{
                data:[result.risk_score,100-result.risk_score],
                backgroundColor:["#1f7a4c","#e0e0e0"],
                borderWidth:0
            }]
        },
        options:{
            cutout:"80%",
            plugins:{ legend:{ display:false } }
        }
    });

    animateNumber("simScore",result.risk_score);

};

});
