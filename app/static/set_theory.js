var canvas = document.getElementById("myCanvas");
var ctx = canvas.getContext("2d");

var x = 0;
var y = 0;

function getMousePos(canvas, evt) {
    var rect = canvas.getBoundingClientRect();
    return {
        x: (evt.clientX - rect.left) / (rect.right - rect.left) * canvas.width,
        y: (evt.clientY - rect.top) / (rect.bottom - rect.top) * canvas.height
    };
}

function drawEllipse() {
    ctx.beginPath();
    ctx.fillStyle = "black";
    ctx.ellipse(150, 150, 50, 100, 0, 0, 2 * Math.PI);
    ctx.stroke();
};

function drawCircle(x, y) {
    ctx.beginPath();
    ctx.fillStyle = "black";
    ctx.arc(x, y, 50, 0, 2 * Math.PI);
    ctx.stroke();
};

output = document.getElementById("text")


canvas.addEventListener("mousemove", (e) => {
    

    distance_from_radius = Math.sqrt((e.offsetX - 150) ** 2 + (e.offsetY - 150) ** 2);

    if (distance_from_radius < 50) {
        output.innerHTML = "(" + e.offsetX + ", " + e.offsetY + ")" + " Inside!";
    } else {
        output.innerHTML = "(" + e.offsetX + ", " + e.offsetY + ")";
    };
});

drawCircle(150,150)




