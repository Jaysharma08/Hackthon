let speedElement = document.getElementById("speed");
let statusElement = document.getElementById("status");
let potholeElement = document.getElementById("potholes");
let distanceElement = document.getElementById("distance");

let totalPotholes = 0;
let totalDistance = 0;
let previousLat = null;
let previousLng = null;

let ctx = document.getElementById('speedChart').getContext('2d');

let speedChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Speed (km/h)',
            data: [],
            borderColor: '#22c55e',
            borderWidth: 2,
            tension: 0.4
        }]
    },
    options: {
        scales: {
            y: { beginAtZero: true }
        }
    }
});

let tripRunning = false;

function startTrip(){
    fetch("/start_trip")
    .then(res => res.json())
    .then(data => {
        alert("Trip Started");
        tripRunning = true;
        totalPotholes = 0;
        totalDistance = 0;
        potholeElement.innerText = 0;
        distanceElement.innerText = "0 km";
    });
}

function endTrip(){
    if(tripRunning){
        window.location.href = "/end_trip";
        tripRunning = false;
    }
}

function calculateDistance(lat1, lon1, lat2, lon2){
    const R = 6371;
    const dLat = (lat2-lat1) * Math.PI/180;
    const dLon = (lon2-lon1) * Math.PI/180;

    const a =
        Math.sin(dLat/2) * Math.sin(dLat/2) +
        Math.cos(lat1*Math.PI/180) *
        Math.cos(lat2*Math.PI/180) *
        Math.sin(dLon/2) *
        Math.sin(dLon/2);

    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

setInterval(() => {
    if(!tripRunning) return;

    fetch("/api/live")
    .then(res => res.json())
    .then(data => {

        speedElement.innerText = data.speed + " km/h";

        if(data.pothole === 1){
            statusElement.innerText = "UNSAFE";
            statusElement.className = "unsafe";
            totalPotholes++;
            potholeElement.innerText = totalPotholes;
        } else {
            statusElement.innerText = "SAFE";
            statusElement.className = "safe";
        }

        if(previousLat !== null){
            let d = calculateDistance(previousLat, previousLng, data.lat, data.lng);
            totalDistance += d;
            distanceElement.innerText = totalDistance.toFixed(2) + " km";
        }

        previousLat = data.lat;
        previousLng = data.lng;

        speedChart.data.labels.push("");
        speedChart.data.datasets[0].data.push(data.speed);

        if(speedChart.data.labels.length > 15){
            speedChart.data.labels.shift();
            speedChart.data.datasets[0].data.shift();
        }

        speedChart.update();
    });

}, 2000);