var imageContainer = document.getElementById("imageContainer")!;
function imageContainerScroll() {
    console.log(imageContainer.scrollLeft, imageContainer.scrollTop);
}
imageContainer.addEventListener('scroll', imageContainerScroll);

var image = document.getElementById("image") as HTMLImageElement;

async function streamForever() {
    while (true) {
        let response = await fetch("/current_stream");
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
            console.log("readLen(", len, ") returning with length", ret.length);
            return ret;
        }    
    
        while (true) {
            let lenArray = await readLen(4);
            if (lenArray) {
                let len = new DataView(lenArray.buffer).getUint32(0, true);
                console.log("got len=", len);
                let jpeg = await readLen(len);
                if (jpeg) {
                    console.log("got jpeg, len", jpeg.length);
                    image.src = URL.createObjectURL(new Blob([jpeg.buffer]), {type: "image/jpeg"});
                    continue;
                }
            }
            break;
        }
    }
}

streamForever();

console.log("webConsole.ts loaded v2");

