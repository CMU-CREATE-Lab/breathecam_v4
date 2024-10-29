let slowFocusImageContainer;
let slowFocusImage;
let zoomOutImage;
let fastFocusImage;

type ScrollPos = { mode: string, x: number, y: number };
let scrollPos: ScrollPos = { mode: "ZoomOut", x: -1, y: -1 };

document.addEventListener('DOMContentLoaded', () => {
    slowFocusImageContainer = requireElementIdType("slowFocusImageContainer", HTMLDivElement);
    slowFocusImage = requireElementIdType("slowFocusImage", HTMLImageElement);
    zoomOutImage = requireElementIdType("zoomOutImage", HTMLImageElement);
    fastFocusImage = requireElementIdType("fastFocusImage", HTMLImageElement);
    initButtons();
    initResize();
    streamLoop();
});

function requireElementIdType<EltType extends HTMLElement>(id: string, constructor:{new():EltType}): EltType {
    let elt = document.getElementById(id);
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
        viewState = new ViewState("ZoomOut");
        scrollPos.mode = "ZoomOut";
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
const zoomOutMode = new ZoomOutMode();

// While SlowFocusMode works, it is the only mode that tries to keep viewState 
// updated, and yet viewState is not actually needed. The panning in SlowFocus mode
// happens all on the client side, so there is no need to do writeScrollPos(), so
// no need to have the viewState mechanisim to keep track of when to do writeScrollPos().
// Probably viewState mechanism should just be ripped out.  Also the viewState updating
// is buggy.
//
// What does need to do writeScrollPos() is FastFocusMode, and yet it is not clear how
// to get this to work. I don't see how to use actual scrollbars, so once again it is unclear 
// if viewState is relevant.
class SlowFocusMode implements Mode {
    async enter() {
        viewState = new ViewState("SlowFocus");
        scrollPos.mode = "SlowFocus";
    }    
    url = "/currentStream";
    async receiveImage(objectUrl: string) {
        slowFocusImage.src = objectUrl;
        await slowFocusImage.decode();
        slowFocusImageContainer.style.display = "block";
        slowFocusImage.style.display = "block";
        //onWindowResize();
        updateViewState({
            imageWidth: slowFocusImage.width, 
            imageHeight: slowFocusImage.height, 
            containerWidth: slowFocusImageContainer.clientWidth, 
            containerHeight: slowFocusImageContainer.clientHeight});
    }
    async exit() {
        slowFocusImageContainer.style.display = "none";
        slowFocusImage.style.display = "none";
    }
};
const slowFocusMode = new SlowFocusMode()

class FastFocusMode implements Mode {
    async enter() {
        viewState = new ViewState("FastFocus");
        scrollPos.mode = "FastFocus";
    }
    url = "/currentStream";
    async receiveImage(objectUrl: string) {
        fastFocusImage.src = objectUrl;
        await fastFocusImage.decode();
        fastFocusImage.style.display = "block";
    }
    async exit() {
        zoomOutImage.style.display = "none";
    }
};
const fastFocusMode = new FastFocusMode();

let streamReader = null;

function cancelStream() {
    if (streamReader) {
        console.log("cancelStream()");
        try {
            streamReader.cancel();
        } catch {}
        streamReader = null;
    }
}

let modeButtons;
function initButtons() {
    modeButtons = new RadioButtonHighlight([
        { id: "zoomOutButton", mode: zoomOutMode, initialSelection: true},
        { id: "slowFocusButton", mode: slowFocusMode},
        { id: "fastFocusButton", mode: fastFocusMode}
    ],
    cancelStream
    );
};

type ViewStateUpdate = {
    imageWidth?: number;
    imageHeight?: number;
    containerWidth?: number;
    containerHeight?: number;
};

class ViewState {
    mode: string;
    imageWidth: number;
    imageHeight: number;
    containerWidth: number;
    containerHeight: number;
    constructor(mode, imageWidth = NaN, imageHeight = NaN, containerWidth = NaN, containerHeight = NaN) {
        this.mode = mode;
        this.imageWidth = imageWidth;
        this.imageHeight = imageHeight;
        this.containerWidth = containerWidth;
        this.containerHeight = containerHeight;
    }
    isValid() {
        return !(isNaN(this.imageWidth) || isNaN(this.imageHeight) || isNaN(this.containerWidth) || isNaN(this.containerHeight));
    }
    equals(rhs: ViewState) {
        return this.mode === rhs.mode && this.imageWidth === rhs.imageWidth && this.imageHeight == rhs.imageHeight &&
            this.containerWidth === rhs.containerWidth && this.containerHeight === rhs.containerHeight
    }
    scrollBarsFromScrollPos(scrollPos: ScrollPos) {
        return {
            scrollLeft: scrollPos.x * this.imageWidth - this.containerWidth / 2,
            scrollTop: scrollPos.y * this.imageHeight - this.containerHeight / 2
        }
    }
    scrollPosFromScrollBars(scroll: { scrollLeft: number, scrollTop: number }) {
        return {
            mode: this.mode,
            x: (scroll.scrollLeft + this.containerWidth / 2) / this.imageWidth,
            y: (scroll.scrollTop + this.containerHeight / 2) / this.imageHeight
        };
    }
    withUpdate(update: ViewStateUpdate) {
        return new ViewState(
            this.mode,
            update.imageWidth ?? this.imageWidth,
            update.imageHeight ?? this.imageHeight,
            update.containerWidth ?? this.containerWidth,
            update.containerHeight ?? this.containerHeight
        );
    }
}

let viewState = new ViewState("ZoomOut");

// If image container changes size (from e.g. window resize), or if image itself changes size (also triggered by the first image loaded),
// update the HTML scrollbars from current scrollPos.
let firstFrameLoaded = false;
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

// Push scrollPos out to the server, should be done whenever it changes, such as on mode change
function writeScrollpos () {
    console.log(`writeScrollpos ${JSON.stringify(scrollPos)}`);

    fetch('/writeScrollpos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(scrollPos)
    });
}

// Capture scroll events after first camera frame is loaded
async function onImageContainerScroll() {
    if (!firstFrameLoaded) return; // Ignore scroll events until first frame is loaded
    scrollPos = viewState.scrollPosFromScrollBars({
            scrollLeft: slowFocusImageContainer.scrollLeft,
            scrollTop: slowFocusImageContainer.scrollTop
        });
    writeScrollpos();
}

let imageQueue: string[] = [];
let isImageProcessing: boolean = false;

async function stream(mode: Mode) {
    console.log(`streamForever ${mode.constructor.name}`);
    await mode.enter();
    writeScrollpos();
    try {
        while (mode === modeButtons.selected?.mode) {
            console.log(`fetching ${mode.url}`);
            let response = await fetch(mode.url);
            streamReader = response.body.getReader();
            let buf = new Uint8Array();

            async function readLen(len: number): Promise<Uint8Array | null> {
                while (buf.length < len) {
                    let { value, done } = await streamReader.read();
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
                        let objectUrl = URL.createObjectURL(new Blob([jpeg.buffer], { type: "image/jpeg" }));
                        imageQueue.push(objectUrl);
                        processImageQueue(mode);
                        continue;
                    }
                }
                break;
            }

            cancelStream();
        }
    } finally {
        cancelStream();
        await mode.exit();
    }
}

async function processImageQueue(mode: Mode) {
    if (isImageProcessing || imageQueue.length === 0) return;

    isImageProcessing = true;
    let objectUrl = imageQueue.shift();

    try {
        await mode.receiveImage(objectUrl);
    } catch (error) {
        console.error(`Error processing image ${objectUrl}:`, error);
    } finally {
        URL.revokeObjectURL(objectUrl);
        isImageProcessing = false;
        processImageQueue(mode); // Process the next image in the queue
    }
}

function initResize () {
    slowFocusImageContainer.addEventListener("scroll", onImageContainerScroll);
    window.addEventListener("resize", onWindowResize); 
    onWindowResize();
}

async function streamLoop() {
    while (true) {
        let mode = modeButtons.selected?.mode;
        if (mode) {
            await stream(mode);
        } else {
            await sleep(0.1);
        }
    }
}

console.log("webConsole.ts loaded v4");
