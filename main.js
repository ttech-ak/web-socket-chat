const websocket = new WebSocket("ws://localhost:8001/");

websocket.addEventListener("message", ({data}) => {
    setError(data);
});

function setError(err){
    errDiv = document.querySelector("#errdiv");
    errDiv.innerText += "\n" + err;
}

function setNick(){
    let nick = document.getElementById("newNick").value;
    console.log("setNick: got nick: " + nick);
    nick = nick.trim()
    console.log("setNick: setting to: " + nick);
    if (nick == ""){
	setError("nick cannot be empty");
	return;
    }
    msg = {action: "nick", nick: nick};
    websocket.send(JSON.stringify(msg));
}

function joinChan(){
    let chan = document.getElementById("newChan").value.trim();
    if (chan == ""){
	setError("chan cannot be empty");
	return;
    }
    msg = {action: "join", channel: chan};
    console.log("joinchan: sending:" + JSON.stringify(msg))
    websocket.send(JSON.stringify(msg));
}
function sendMsg(){
    let chan = document.getElementById("msgChan").value.trim();
    let msg = document.getElementById("msgMsg").value.trim();
    if (chan == ""){
	setError("chan cannot be empty");
	return;
    }
    if (msg == ""){
	setError("msg cannot be empty");
	return;
    }
    msg = {action: "privmsg", channel: chan, message: msg};
    console.log("sendmsg: sending:" + JSON.stringify(msg))
    websocket.send(JSON.stringify(msg));
}
