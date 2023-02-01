var togglebtn = document.querySelector('.toggle-btn');
var leftSidebarWrapper = document.querySelector('.left-sidebar-container');
var leftMenu = document.querySelector('.left-menu');

var togglebtn = document.getElementsByClassName("toggle-btn"); // <- this gives you  a HTMLCollection 
for (var i = 0; i < togglebtn.length; i++) {
  togglebtn[i].onclick = function() {
    leftSidebarWrapper.classList.toggle("open");
    leftMenu.classList.toggle("open");
  }
}