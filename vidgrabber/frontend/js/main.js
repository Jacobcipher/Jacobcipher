document.addEventListener('DOMContentLoaded', () => {
    const videoUrlInput = document.getElementById('videoUrl');
    const submitBtn = document.getElementById('submitBtn');
    const messageDiv = document.getElementById('message'); // For displaying messages

    if (submitBtn) {
        submitBtn.addEventListener('click', async () => {
            const url = videoUrlInput.value.trim();
            if (!url) {
                displayMessage('Please paste a video URL.', 'error');
                return;
            }

            submitBtn.disabled = true;
            submitBtn.textContent = 'Processing... Please wait.'; // Updated message
            displayMessage('Requesting video... This may take a moment.', 'info');

            try {
                // Point to the new backend endpoint for muxing and direct download
                const response = await fetch('http://127.0.0.1:8000/api/process_and_download_video', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ url: url }),
                });

                if (!response.ok) {
                    // Try to parse error detail from backend if it's a JSON response
                    let errorDetail = `HTTP error! status: ${response.status}`;
                    try {
                        const errorData = await response.json();
                        errorDetail = errorData.detail || errorDetail;
                    } catch (e) {
                        // If response is not JSON, use the default errorDetail
                        console.warn('Could not parse error response as JSON.');
                    }
                    throw new Error(errorDetail);
                }

                // If response.ok is true, the browser should be initiating a download
                // due to Content-Disposition header from the backend.
                // We can try to get the filename from the Content-Disposition header for the message.
                let filename = "your video";
                const disposition = response.headers.get('content-disposition');
                if (disposition && disposition.indexOf('attachment') !== -1) {
                    const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                    const matches = filenameRegex.exec(disposition);
                    if (matches != null && matches[1]) {
                        filename = matches[1].replace(/['"]/g, '');
                    }
                }

                displayMessage(`Download for "${filename}" should start automatically. If not, please check your browser's download manager.`, 'success');
                // No redirection to result.html for this direct download flow.
                // The existing result.html logic (displayVideoResults, localStorage) is now bypassed for this button.
                // We can decide later if we want a hybrid approach or separate buttons.

            } catch (error) {
                console.error('Error processing video:', error);
                displayMessage(`Error: ${error.message}`, 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Download'; // Reset button text
            }
        });
    }

    // Function to display messages on the page
    function displayMessage(message, type = 'info') {
        if (messageDiv) {
            messageDiv.textContent = message;
            messageDiv.className = `message ${type}`;
            messageDiv.style.display = 'block';
        } else {
            // Fallback if messageDiv is not on the current page
            // This should ideally not be needed if index.html always has a messageDiv
            alert(message);
        }
    }

    // The result.html display logic (displayVideoResults function and its call)
    // is no longer directly used by the main download button.
    // It could be repurposed later if we implement a "get info first, then download" flow
    // or for displaying choices (like different resolutions/formats).
    // For now, it remains here but is dormant for the primary download action.
    if (window.location.pathname.endsWith('result.html')) {
        const videoDataString = localStorage.getItem('videoData');
        if (videoDataString) {
            try {
                const videoData = JSON.parse(videoDataString);
                // displayVideoResults(videoData); // This function would need to be available
                                                // or its definition moved/copied here if result.html is still used.
                                                // For now, commenting out as the flow changed.
                console.log("Result page loaded, data found in localStorage but not displayed by this script version.");
                const resultsDiv = document.getElementById('results');
                if(resultsDiv) resultsDiv.innerHTML = '<p>This page is not currently used for direct downloads. Please use the main page.</p>';
            } catch (e) {
                console.error("Error parsing video data from localStorage", e);
                const resultsDiv = document.getElementById('results');
                if(resultsDiv) resultsDiv.innerHTML = '<p>Error displaying video data.</p>';
            }
        } else {
            const resultsDiv = document.getElementById('results');
            if(resultsDiv) resultsDiv.innerHTML = '<p>No video data found.</p>';
        }
    }
});

// The displayVideoResults function might be removed or refactored later
// if result.html is fully deprecated or changed.
// For now, it's left here to avoid breaking result.html entirely if it's accessed.
function displayVideoResults(data) {
    // ... (existing function, currently not called by the main download flow) ...
    // (This function's content is the same as in the previous version of main.js,
    //  including the audio info display logic)
    const resultsDiv = document.getElementById('results');
    if (!resultsDiv) return;
    resultsDiv.innerHTML = '';
    if (data.error) {
        resultsDiv.innerHTML = `<p class="error-message">Error: ${data.error}</p>`;
        return;
    }
    const titleElement = document.createElement('h2');
    titleElement.textContent = data.title || 'Untitled Video';
    resultsDiv.appendChild(titleElement);

    if (data.thumbnail) {
        const thumbnailElement = document.createElement('img');
        thumbnailElement.src = data.thumbnail;
        thumbnailElement.alt = 'Video Thumbnail';
        thumbnailElement.style.maxWidth = '300px';
        thumbnailElement.style.marginBottom = '15px';
        resultsDiv.appendChild(thumbnailElement);
    }

    if (data.uploader) {
        const uploaderElem = document.createElement('p');
        uploaderElem.textContent = `Uploader: ${data.uploader}`;
        resultsDiv.appendChild(uploaderElem);
    }
    if (data.duration_string) {
        const durationElem = document.createElement('p');
        durationElem.textContent = `Duration: ${data.duration_string}`;
        resultsDiv.appendChild(durationElem);
    }

    const formatsList = document.createElement('ul');
    formatsList.className = 'formats-list';

    if (data.formats && data.formats.length > 0) {
        data.formats.forEach(format => {
            const listItem = document.createElement('li');

            let formatDescription = `${format.format_note || format.resolution || (format.width && format.height ? `${format.width}x${format.height}` : '') || format.format_id} (${format.ext})`;

            if (format.filesize_approx) {
                formatDescription += ` - ${(format.filesize_approx / 1024 / 1024).toFixed(2)} MB`;
            } else if (format.tbr) {
                 formatDescription += ` ~${format.tbr.toFixed(2)} kbps`;
            }

            let audioInfo = "";
            if (!format.acodec || format.acodec === 'none') {
                audioInfo = " (Video Only, No Audio)";
            } else {
                audioInfo = ` (Audio: ${format.acodec})`;
            }

            listItem.innerHTML = `
                <span>${formatDescription}${audioInfo}</span>
                <div class="format-buttons">
                    <a href="${format.url}" target="_blank" download class="download-btn">Download</a>
                    <button class="copy-btn" data-url="${format.url}">Copy Link</button>
                </div>
            `;
            formatsList.appendChild(listItem);
        });
    } else {
        const noFormatsItem = document.createElement('li');
        noFormatsItem.textContent = 'No suitable downloadable formats found for this video, or there was an issue fetching them.';
        formatsList.appendChild(noFormatsItem);
    }
    resultsDiv.appendChild(formatsList);

    document.querySelectorAll('.copy-btn').forEach(button => {
        button.addEventListener('click', async (e) => {
            const urlToCopy = e.target.dataset.url;
            try {
                await navigator.clipboard.writeText(urlToCopy);
                e.target.textContent = 'Copied!';
                setTimeout(() => { e.target.textContent = 'Copy Link'; }, 2000);
            } catch (err) {
                console.error('Failed to copy: ', err);
                alert('Failed to copy link.');
            }
        });
    });
    console.warn("displayVideoResults function is present but not actively used by the main download button in this script version.");
}
