var imageContainer = document.getElementById("imageContainer") as HTMLDivElement;

var image = document.getElementById("image") as HTMLImageElement;

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
            imageContainer.scrollLeft = scrollLeft;
            imageContainer.scrollTop = scrollTop;
            console.log(imageContainer.scrollLeft, imageContainer.scrollTop);
            firstFrameLoaded = true;
        }
    }
}

async function onImageLoad() {
    updateViewState({imageWidth: image.width, imageHeight: image.height});
}

async function onWindowResize() {
    updateViewState({containerWidth: imageContainer.clientWidth, containerHeight: imageContainer.clientHeight});
}

// Capture scroll events after first camera frame is loaded
async function onImageContainerScroll() {
    if (!firstFrameLoaded) return; // Ignore scroll events until first frame is loaded
    scrollPos = viewState.scrollPosFromScrollBars({
            scrollLeft: imageContainer.scrollLeft,
            scrollTop: imageContainer.scrollTop
        });

    console.log(`writeScrollpos ${JSON.stringify(scrollPos)}`);

    fetch('/writeScrollpos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(scrollPos)
    });
}

let lastObjectUrl: string = "";

async function streamForever() {
    console.log("streamForever");
    scrollPos = await (await fetch("/readScrollpos")).json();

    while (true) {
        console.log("fetching currentStream");
        let response = await fetch("/currentStream");

        let reader = response.body.getReader();

        let buf = new Uint8Array();

        // Return ArrayBuf of length len, reading reader as needed
        async function readLen(len: number): Promise<Uint8Array|null> {
            while (buf.length < len) {
                let {value, done} = await reader.read();
                if (value.length) {
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
                    image.src = URL.createObjectURL(new Blob([jpeg.buffer], {type: "image/jpeg"}));
                    if (lastObjectUrl) {
                        URL.revokeObjectURL(lastObjectUrl);
                        lastObjectUrl = image.src;
                    }
                    // Successful frame;  get next one
                    continue;
                }
            }
            // Unsuccessful frame;  exit loop and re-fetch /currentStream
            break;
        }
    }
}

imageContainer.addEventListener('scroll', onImageContainerScroll);
image.addEventListener("load", onImageLoad);
window.addEventListener('resize', onWindowResize);
onWindowResize();

streamForever();

console.log("webConsole.ts loaded v2");

