function register() {
    let name = document.getElementById("name").value;

    if (name == "") {
        alert("Please enter your name");
    }
    else {
        alert("Registration successful!");
    }
}