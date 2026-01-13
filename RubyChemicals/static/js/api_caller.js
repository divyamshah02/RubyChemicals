async function callApi(method, url, bodyData = null, csrfToken = '', media_upload = false) {
    // toggle_loader()
    try {
        // Validate method and URL
        if (typeof method !== 'string' || typeof url !== 'string') {
            throw new Error("Invalid method or URL");
        }

        let headers_data = {}

        if (media_upload) {
            headers_data = {
                ...(csrfToken && { 'X-CSRFToken': csrfToken }),
            };
        }
        else {
            headers_data = {
                'Content-Type': 'application/json',
                ...(csrfToken && { 'X-CSRFToken': csrfToken }),
            };
        }

        // Prepare request options
        const options = {
            method: method.toUpperCase(),
            headers: headers_data
        };

        // Add bodyData for non-GET requests
        if (method.toUpperCase() !== 'GET' && bodyData) {
            if (media_upload) {
                options.body = bodyData;
            }
            else {
                options.body = JSON.stringify(bodyData);
            }
        }

        // Make the fetch request
        const response = await fetch(url, options);
        // console.log(response)

        // Check for HTTP errors
        // if (!response.ok) {
        //     throw new Error(`HTTP Error: ${response.status} - ${response.statusText}`);
        // }


        try {
            const data = await response.json();
            // toggle_loader()
            return [true, data];
        }
        catch (error) {
            console.log('Error in parsing JSON:', error);
            // window.location.href=`/login/`;            
        }

        // Parse the JSON response
        // data = await response.json();

        // Return success flag and data

    } catch (error) {
        // Log and return failure flag with error
        console.error("API Call Error:", error);
        // toggle_loader()
        return [false, error.message || "An unknown error occurred"];
    }
}

function toQueryString(params) {
    return Object.keys(params)
        .map(key => encodeURIComponent(key) + '=' + encodeURIComponent(params[key]))
        .join('&');
}


// Example Usage of api caller function
async function exampleApiCallerPOST() {
    const bodyData = {
        email: "divyamshah1234@gmail.com",
        password: "divym",
    };

    const url = "{% url 'login-api-list' %}";
    const [success, result] = await callApi("POST", url, bodyData, "{{csrf_token}}");
    if (success) {
        console.log("Result:", result);
    } else {
        console.error("Login User Failed:", result);
    }
}


async function exampleApiCallerGET() {
    const Params = {
        user_id: "IO7169754192",
    };

    const url = "{% url 'user-list' %}?" + toQueryString(Params); // Construct the full URL with query params
    const [success, result] = await callApi("GET", url);
    if (success) {
        console.log("GET User Success:", result);
    } else {
        console.error("GET User Failed:", result);
    }
}

function toggle_loader() {
    let existingLoader = document.getElementById('dynamic-page-loader');

    if (existingLoader) {
        // If loader exists, remove it
        existingLoader.remove();
    } else {
        // Create loader container
        const loader = document.createElement('div');
        loader.id = 'dynamic-page-loader';
        loader.style.position = 'fixed';
        loader.style.top = 0;
        loader.style.left = 0;
        loader.style.width = '100%';
        loader.style.height = '100%';
        loader.style.background = 'rgba(255, 255, 255, 0.7)';
        loader.style.display = 'flex';
        loader.style.justifyContent = 'center';
        loader.style.alignItems = 'center';
        loader.style.zIndex = 9999;

        // Create spinner
        const spinner = document.createElement('div');
        spinner.style.width = '3rem';
        spinner.style.height = '3rem';
        spinner.style.border = '6px solid #ccc';
        spinner.style.borderTop = '6px solid #8b6f47';
        spinner.style.borderRadius = '50%';
        spinner.style.animation = 'spin 1s linear infinite';

        // Inject keyframe animation (once)
        if (!document.getElementById('loader-spin-style')) {
            const style = document.createElement('style');
            style.id = 'loader-spin-style';
            style.innerHTML = `
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            `;
            document.head.appendChild(style);
        }

        loader.appendChild(spinner);
        document.body.appendChild(loader);
    }
}

function openDoc(url, file_name) {
    const modal = document.createElement("div");
    modal.className = "modal fade";
    modal.id = "viewDocumentModal";
    modal.tabIndex = -1;
    modal.setAttribute("aria-labelledby", "viewDocumentModalLabel");
    modal.setAttribute("aria-hidden", "true");

    // Modal dialog
    const modalDialog = document.createElement("div");
    modalDialog.className = "modal-dialog";

    // Modal content
    const modalContent = document.createElement("div");
    modalContent.className = "modal-content";

    // Modal header
    const modalHeader = document.createElement("div");
    modalHeader.className = "modal-header";

    const title = document.createElement("h1");
    title.className = "modal-title fs-5 text-wrap text-break";
    title.id = "viewDocumentModalLabel";
    title.innerText = file_name;

    const closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.className = "btn-close";
    closeBtn.setAttribute("data-bs-dismiss", "modal");
    closeBtn.setAttribute("aria-label", "Close");

    modalHeader.appendChild(title);
    modalHeader.appendChild(closeBtn);

    // Modal body
    const modalBody = document.createElement("div");
    modalBody.className = "modal-body";

    const viewerDiv = document.createElement("div");
    viewerDiv.id = "document-viewer";
    viewerDiv.className = "viewer";

    modalBody.appendChild(viewerDiv);

    // Modal footer
    const modalFooter = document.createElement("div");
    modalFooter.className = "modal-footer";

    const downloadBtn = document.createElement("a");
    downloadBtn.className = "btn btn-primary";
    downloadBtn.id = "viewDocumentModalDownloadBtn";
    downloadBtn.href = url;
    downloadBtn.download = file_name;
    downloadBtn.innerHTML = "<b>Download Bill</b>";

    modalFooter.appendChild(downloadBtn);

    // Build modal structure
    modalContent.appendChild(modalHeader);
    modalContent.appendChild(modalBody);
    modalContent.appendChild(modalFooter);

    modalDialog.appendChild(modalContent);
    modal.appendChild(modalDialog);

    // Append to body
    document.body.appendChild(modal);

    const viewer = document.getElementById('document-viewer');
    const viewerElement = document.getElementById("document-viewer");
    viewer.innerHTML = ''; // Clear previous content
    // Get the file extension
    const extension = url.split('.').pop().toLowerCase();
    console.log(extension)
    document.getElementById('viewDocumentModalDownloadBtn').download = `${file_name}.${extension}`

    // Create the appropriate element based on the file type
    if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(extension)) {
        // Image
        const img = document.createElement('img');
        img.src = url;
        img.alt = "Image document";
        img.className = 'img-fluid';
        viewer.appendChild(img);
    }
    else if (extension === 'pdf') {
        // Custom PDF Viewer
        console.log('Rendering PDF:', url);

        // Create navigation controls
        const controls = document.createElement('div');
        controls.id = 'pdf-controls';
        controls.innerHTML = `
                    <button id="prev-page" class="btn btn-primary eh-btn-blue-primary-no-hover"><i class="fa fa-circle-chevron-left"></i></button>
                    <span id="page-info">Page <span id="current-page">1</span> of <span id="total-pages">1</span></span>
                    <button id="next-page" class="btn btn-primary eh-btn-blue-primary-no-hover"><i class="fa fa-circle-chevron-right"></i></button>
                `;
        viewer.appendChild(controls);

        // Create canvas for rendering the PDF
        const canvas = document.createElement('canvas');
        canvas.id = 'pdf-render';
        viewer.appendChild(canvas);

        // Initialize PDF.js
        const pdfjsLib = window['pdfjs-dist/build/pdf'];
        const pdfRender = canvas;
        const ctx = pdfRender.getContext('2d');
        let pdfDoc = null;
        let currentPage = 1;
        let totalPages = 0;

        // Render the current page
        function renderPage(pageNum) {
            pdfDoc.getPage(pageNum).then((page) => {
                const viewport = page.getViewport({ scale: 1.5 });
                pdfRender.width = viewport.width;
                pdfRender.height = viewport.height;

                const renderContext = {
                    canvasContext: ctx,
                    viewport: viewport,
                };
                page.render(renderContext);
                document.getElementById('current-page').textContent = pageNum;
            });
        }

        // Load the PDF and initialize the viewer
        pdfjsLib.getDocument(url).promise.then((pdf) => {
            pdfDoc = pdf;
            totalPages = pdf.numPages;
            document.getElementById('total-pages').textContent = totalPages;
            renderPage(currentPage);
        });

        // Add event listeners for navigation
        document.getElementById('prev-page').addEventListener('click', () => {
            if (currentPage <= 1) return;
            currentPage--;
            renderPage(currentPage);
        });

        document.getElementById('next-page').addEventListener('click', () => {
            if (currentPage >= totalPages) return;
            currentPage++;
            renderPage(currentPage);
        });
    }
    else if (['mp4', 'webm', 'ogg'].includes(extension)) {
        // Video
        const video = document.createElement('video');
        video.src = url;
        video.controls = true;
        video.style.width = "100%";
        video.style.maxHeight = '500px';
        viewer.appendChild(video);
    }
    else if (['mp3', 'wav', 'ogg'].includes(extension)) {
        // Audio
        const audio = document.createElement('audio');
        audio.src = url;
        audio.controls = true;
        audio.style.width = "100%";
        audio.style.maxHeight = '500px';
        viewer.appendChild(audio);
    }
    else {
        // Unsupported file type
        viewer.innerHTML = `<p>Unsupported document type: ${extension}, Please download to view!</p>`;
    }

    // const myModal = new bootstrap.Modal(document.getElementById('viewDocumentModal'));
    // myModal.show();

    const bsModal = new bootstrap.Modal(modal);

    // Remove modal from DOM after it is fully hidden
    modal.addEventListener("hidden.bs.modal", () => {
        modal.remove();
    });

    // Show modal
    bsModal.show();

}
