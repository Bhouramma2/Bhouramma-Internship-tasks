function login() {
    let username = document.getElementById("username").value;
    let password = document.getElementById("password").value;

    if (username == "" || password == "") {
        alert("Please enter username and password");
    } else {
        alert("Login successful!");
    }
}

