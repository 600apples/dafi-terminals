const WSURL = (() => {
    let urlBase = window.location.href.split(/\?|#/, 1)[0].replace('http', 'ws');
    return urlBase + (urlBase[urlBase.length - 1] === '/' ? '' : '/');
})();

let terminalSock;

const DATA = 1;
const RESIZE = 2;

window.onload = async () => {
    await new DirectorSocket().start();
};


class DirectorSocket {
    async start() {
        let directorUrl = WSURL + 'director';
        this.sock = new WebSocket(directorUrl);
        this.sock.onmessage = this.onmessage;
        this.sock.onerror = this.onerror;
        this.sock.onclose = this.onclose;
    }

    onmessage(msg) {
        let data = JSON.parse(msg.data);
        let terminalListUl = document.getElementById("terminal-list");
        terminalListUl.innerHTML = '';
        for (var i = 0; i < data.length; i++) {
            let worker = data[i];
            let fillColor = worker.active ? '#007bff' : '#ff3a11';
            let workerItem = document.createElement("li");
            workerItem.className = "terminal-worker-mdc";
            workerItem.id = worker.process_name;
            workerItem.innerHTML = `<div class="terminal-worker-mdc-icon">
                                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                                            <g>
                                                <path fill="none" d="M0 0h24v24H0z"/>
                                                <path fill="${fillColor}"
                                                d="M11 12l-7.071 7.071-1.414-1.414L8.172 12 2.515 6.343 3.929 4.93 11 12zm0 7h10v2H11v-2z"/>
                                            </g>
                                        </svg>
                                    </div>
                                    <div class="terminal-mdc-card">
                                        <h4>${worker.process_name}</h4>
                                        <p>host: ${worker.host}</p>
                                        <p>mac: ${worker.mac}</p>
                                    </div>`;

            if (worker.active) {
                workerItem.onclick = createTerminal;
            } else {
                let workerCloseButton = document.createElement("a");
                workerCloseButton.className = "close-terminal";
                workerCloseButton.role = "button";
                workerItem.prepend(workerCloseButton);
                workerCloseButton.onclick = (ev) => {
                    ev.preventDefault();
                    ev.stopPropagation();
                    let targetLi = ev.target.closest(".terminal-worker-mdc");
                    this.send(JSON.stringify({
                        "command": "delete_terminal",
                        "term_id": targetLi.id,
                    }))
                };
            }
            terminalListUl.appendChild(workerItem);

        }
    }

    onerror(e) {
        console.error(e);
    };

    onclose(e) {
        console.log("Director socket has been closed.")
    };
}


async function createTerminal(ev) {
    ev.preventDefault();
    ev.stopPropagation();

    let targetLi = ev.target.closest(".terminal-worker-mdc");
    if (targetLi.className.includes("selected")) {
        console.log("This terminal is already active");
        return
    }

     if (terminalSock) {
        terminalSock.close()
    }
    let workerId = targetLi.id;

    Array.prototype.slice.call(document.querySelectorAll('.terminal-worker-mdc')).forEach(function (element) {
        element.classList.remove('selected');
    });
    // add the selected class to the element that was clicked
    targetLi.classList.add('selected');

    let terminalUrl = WSURL + `terminal?worker_id=${workerId}`;
    terminalSock = new WebSocket(terminalUrl);

    let encoding = 'utf-8';
    let decoder = TextDecoder ? new TextDecoder(encoding) : encoding;
    let termOptions = {
        cursorBlink: true,
        theme: {
            background: 'black',
            foreground: 'white'
        }
    };
    // if (url_opts_data.fontsize) {
    //   var fontsize = window.parseInt(url_opts_data.fontsize);
    //   if (fontsize && fontsize > 0) {
    //     termOptions.fontSize = fontsize;
    //   }
    // }

    let terminal = new Terminal(termOptions);

    terminal.fitAddon = new FitAddon.FitAddon();
    terminal.loadAddon(terminal.fitAddon);


    terminalSock.onopen = () => {
        let terminalElem = document.getElementById('terminal');
        terminal.open(terminalElem);
        terminal.fitAddon.fit();

        terminal.focus();
        // state = CONNECTED;
        // title_element.text = url_opts_data.title || default_title;
        // if (url_opts_data.command) {
        //   setTimeout(function () {
        //     sock.send(new Blob([DATA, url_opts_data.command+'\r']));
        //   }, 500);
        // }

        terminal.onData(function (data) {
            terminalSock.send(new Blob([DATA, data]));
        });

    };

    terminalSock.onmessage = function (msg) {
        read_file_as_text(msg.data, term_write, decoder);
    };


    terminalSock.onclose = function (e) {
        terminal.dispose();
    };


    function read_as_text_with_encoding(file, callback, encoding) {
        var reader = new window.FileReader();

        if (encoding === undefined) {
            encoding = 'utf-8';
        }

        reader.onload = function () {
            if (callback) {
                callback(reader.result);
            }
        };

        reader.onerror = function (e) {
            console.error(e);
        };

        reader.readAsText(file, encoding);
    }


    function read_as_text_with_decoder(file, callback, decoder) {
        var reader = new window.FileReader();

        if (decoder === undefined) {
            decoder = new window.TextDecoder('utf-8', {'fatal': true});
        }

        reader.onload = function () {
            var text;
            try {
                text = decoder.decode(reader.result);
            } catch (TypeError) {
                console.log('Decoding error happened.');
            } finally {
                if (callback) {
                    callback(text);
                }
            }
        };

        reader.onerror = function (e) {
            console.error(e);
        };
        reader.readAsArrayBuffer(file);
    }


    function read_file_as_text(file, callback, decoder) {
        if (!window.TextDecoder) {
            read_as_text_with_encoding(file, callback, decoder);
        } else {
            read_as_text_with_decoder(file, callback, decoder);
        }
    }


    function term_write(text) {
        if (terminal) {
            terminal.write(text);
            // if (!terminal.resized) {
            //   resize_terminal(term);
            //   term.resized = true;
            // }
        }
    }


}