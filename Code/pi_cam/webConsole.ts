function requireElementIdType<EltType extends HTMLElement>(id: string, constructor:{new():EltType}): EltType {
    var elt = document.getElementById(id);
    if (!elt) {
        throw Error(`Required dom element id=${id} not found`);
    }
    if (!(elt instanceof constructor)) {
        throw Error(`Dom element id=${id} required to be of type ${constructor.name} but is ${elt.constructor.name}`);
    }
    return elt;
}

function sleep(seconds: number): Promise<void> {
    return new Promise( resolve => {setTimeout(resolve, seconds * 1000)} );
}

type ButtonInfo = {
    id: string;
    initialSelection?: boolean;
    button?: HTMLButtonElement;
    [key: string]: any;
};

class RadioButtonHighlight {
    selected: ButtonInfo;
    updateCallback: (selected: ButtonInfo) => void;
    buttons = {} as {[buttonId: string]: ButtonInfo};

    constructor(buttonInfos: ButtonInfo[], updateCallback: (selected: ButtonInfo)=>void = null) {
        let initialSelection = null;
        for (const buttonInfo of buttonInfos) {
            let button = requireElementIdType(buttonInfo.id, HTMLButtonElement);
            let info: ButtonInfo = Object.assign({}, buttonInfo, {button: button});
            button.addEventListener("click", this.select.bind(this, info.id));
            if (info.initialSelection) initialSelection = info.id;
            this.buttons[info.id] = info;
        }
        this.selected = null;
        this.updateCallback = updateCallback;
        this.select(initialSelection);
    }

    select(buttonId: string|null) {
        let selected = null;
        if (buttonId) {
            selected = this.buttons[buttonId];
            if (!selected) throw new Error(`select: buttonId "${buttonId}" not found`);
        }
        if (selected == this.selected) return;
        if (this.selected) this.selected.button.classList.remove("radioButtonHighlightSelected");
        this.selected = selected;
        if (this.selected) this.selected.button.classList.add("radioButtonHighlightSelected");
        if (this.updateCallback) {
            this.updateCallback(this.selected);
        }
    }
}

interface Mode {
    enter(): Promise<void>;
    url: string;
    receiveImage(objectUrl: string): void;
    exit(): Promise<void>;
}

class ZoomOutMode implements Mode {
    async enter() {
        viewState = new ViewState();
        scrollPos = await (await fetch("/readScrollpos")).json();    
    }
    url = "/currentStream";
    async receiveImage(objectUrl: string) {
        zoomOutImage.src = objectUrl;
        await zoomOutImage.decode();
        zoomOutImage.style.display = "block";
    }
    async exit() {
        zoomOutImage.style.display = "none";
    }
};
let zoomOutMode = new ZoomOutMode();

class SlowFocusMode implements Mode {
    async enter() {
        viewState = new ViewState();
        scrollPos = await (await fetch("/readScrollpos")).json();    
    }    
    url = "/currentStream";
    async receiveImage(objectUrl: string) {
        slowFocusImage.src = objectUrl;
        await slowFocusImage.decode();
        slowFocusImageContainer.style.display = "block";
        slowFocusImage.style.display = "block";
        updateViewState({imageWidth: slowFocusImage.width, imageHeight: slowFocusImage.height});
    }
    async exit() {
        slowFocusImageContainer.style.display = "none";
        slowFocusImage.style.display = "none";
    }
};
let slowFocusMode = new SlowFocusMode()

let streamReader = null;

function cancelStream() {
    console.log("cancelStream()");
    if (streamReader) {
        try {
            streamReader.cancel();
        } catch {}
        streamReader = null;
    }
}

var modeButtons = new RadioButtonHighlight([
    { id: "zoomOutButton", mode: zoomOutMode, initialSelection: true},
    { id: "slowFocusButton", mode: slowFocusMode},
    //{ id: "fastFocusButton", mode: FastFocusMode}
],
    cancelStream
);

var slowFocusImageContainer = requireElementIdType("slowFocusImageContainer", HTMLDivElement);
var slowFocusImage = requireElementIdType("slowFocusImage", HTMLImageElement);
var zoomOutImage = requireElementIdType("zoomOutImage", HTMLImageElement);
var fastFocusImage = requireElementIdType("fastFocusImage", HTMLImageElement);

type ScrollPos = {x: number, y: number};
var scrollPos: ScrollPos = {x: -1, y: -1};

type ViewStateUpdate = {
    imageWidth?: number;
    imageHeight?: number;
    containerWidth?: number;
    containerHeight?: number;
};

class ViewState {
    imageWidth: number;
    imageHeight: number;
    containerWidth: number;
    containerHeight: number;
    constructor(imageWidth=NaN, imageHeight=NaN, containerWidth=NaN, containerHeight=NaN) {
        this.imageWidth = imageWidth;
        this.imageHeight = imageHeight;
        this.containerWidth = containerWidth;
        this.containerHeight = containerHeight;
    }
    isValid() {
        return !(isNaN(this.imageWidth) || isNaN(this.imageHeight) || isNaN(this.containerWidth) || isNaN(this.containerHeight));
    }
    equals(rhs: ViewState) {
        return this.imageWidth === rhs.imageWidth && this.imageHeight == rhs.imageHeight &&
            this.containerWidth === rhs.containerWidth && this.containerHeight === rhs.containerHeight
    }
    scrollBarsFromScrollPos(scrollPos: ScrollPos) {
        return {
            scrollLeft: scrollPos.x * this.imageWidth - this.containerWidth / 2,
            scrollTop: scrollPos.y * this.imageHeight - this.containerHeight / 2
        }
    }
    scrollPosFromScrollBars(scroll: {scrollLeft: number, scrollTop: number}) {
        return {
            x: (scroll.scrollLeft + this.containerWidth / 2) / this.imageWidth,
            y: (scroll.scrollTop + this.containerHeight / 2) / this.imageHeight
        };
    }
    withUpdate(update: ViewStateUpdate) {
        return new ViewState(
            update.imageWidth ?? this.imageWidth,
            update.imageHeight ?? this.imageHeight,
            update.containerWidth ?? this.containerWidth,
            update.containerHeight ?? this.containerHeight
        );
    }
}

var viewState = new ViewState();

// If image container changes size (from e.g. window resize), or if image itself changes size (also triggered by the first image loaded),
// update the HTML scrollbars from current scrollPos.
var firstFrameLoaded = false;
async function updateViewState(update: ViewStateUpdate) {
    let newState = viewState.withUpdate(update);
    if (!newState.equals(viewState)) {
        viewState = newState;
        console.log(`viewState changed to ${JSON.stringify(viewState)}`);
        if (viewState.isValid()) {
            let {scrollLeft, scrollTop} = viewState.scrollBarsFromScrollPos(scrollPos);
            console.log(`setting scrollLeft=${scrollLeft}, scrollTop=${scrollTop}`);
            slowFocusImageContainer.scrollLeft = scrollLeft;
            slowFocusImageContainer.scrollTop = scrollTop;
            console.log(slowFocusImageContainer.scrollLeft, slowFocusImageContainer.scrollTop);
            firstFrameLoaded = true;
        }
    }
}

async function onWindowResize() {
    updateViewState({containerWidth: slowFocusImageContainer.clientWidth, containerHeight: slowFocusImageContainer.clientHeight});
}

// Capture scroll events after first camera frame is loaded
async function onImageContainerScroll() {
    if (!firstFrameLoaded) return; // Ignore scroll events until first frame is loaded
    scrollPos = viewState.scrollPosFromScrollBars({
            scrollLeft: slowFocusImageContainer.scrollLeft,
            scrollTop: slowFocusImageContainer.scrollTop
        });

    console.log(`writeScrollpos ${JSON.stringify(scrollPos)}`);

    fetch('/writeScrollpos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(scrollPos)
    });
}

let lastObjectUrl: string = "";


async function stream(mode: Mode) {
    console.log(`streamForever ${mode.constructor.name}`);
    await mode.enter();

    try {
        while (mode === modeButtons.selected?.mode) {
            console.log(`fetching ${mode.url}`);
            let response = await fetch(mode.url);

            streamReader = response.body.getReader();

            let buf = new Uint8Array();

            // Return ArrayBuf of length len, reading reader as needed
            async function readLen(len: number): Promise<Uint8Array|null> {
                while (buf.length < len) {
                    let {value, done} = await streamReader.read();
                    if (value?.length) {
                        let newBuf = new Uint8Array(buf.length + value.length);
                        newBuf.set(buf, 0);
                        newBuf.set(value, buf.length);
                        buf = newBuf;
                    } else if (done) {
                        return null;
                    }
                }
                let ret = buf.slice(0, len);
                buf = buf.slice(len);
                //console.log("readLen(", len, ") returning with length", ret.length);
                return ret;
            }    
        
            while (true) {
                let lenArray = await readLen(4);
                if (lenArray) {
                    let len = new DataView(lenArray.buffer).getUint32(0, true);
                    let before = performance.now();
                    let jpeg = await readLen(len);
                    if (jpeg) {
                        console.log(`Receiving jpeg len=${jpeg.length} took=${Math.round(performance.now() - before)} ms`);
                        let objectUrl = URL.createObjectURL(new Blob([jpeg.buffer], {type: "image/jpeg"}));
                        await mode.receiveImage(objectUrl);
                        if (lastObjectUrl) {
                            URL.revokeObjectURL(lastObjectUrl);
                        }
                        lastObjectUrl = objectUrl;
                        // Successful frame;  get next one
                        continue;
                    }
                }
                // Unsuccessful frame;  exit loop and re-fetch /currentStream
                break;
            }

            cancelStream();
        }
    } finally {
        cancelStream();
        await mode.exit();
    }
}

slowFocusImageContainer.addEventListener("scroll", onImageContainerScroll);
window.addEventListener("resize", onWindowResize); // TODO: think about resize and whether it will goof up a hidden slowFocusMode
onWindowResize();


async function streamLoop() {
    while (1) { 
        let mode = modeButtons.selected?.mode;
        if (mode) {
            await stream(mode);
        } else {
            await sleep(0.1);
        }
    }
}


console.log("webConsole.ts loaded v2");

streamLoop();
