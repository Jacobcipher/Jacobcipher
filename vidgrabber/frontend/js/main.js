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
            submitBtn.textContent = 'Processing...';
            displayMessage('Fetching video information...', 'info');

            try {
                const response = await fetch('http://127.0.0.1:8000/api/download', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ url: url }),
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
                }

                const data = await response.json();

                if (data.error) {
                    throw new Error(data.error);
                }

                localStorage.setItem('videoData', JSON.stringify(data));
                window.location.href = 'result.html';

            } catch (error) {
                console.error('Error fetching video data:', error);
                displayMessage(`Error: ${error.message}`, 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Download';
            }
        });
    }

    function displayMessage(message, type = 'info') {
        if (messageDiv) {
            messageDiv.textContent = message;
            messageDiv.className = `message ${type}`;
            messageDiv.style.display = 'block';
        } else {
            alert(message);
        }
    }

    if (window.location.pathname.endsWith('result.html')) {
        const videoDataString = localStorage.getItem('videoData');
        if (videoDataString) {
            try {
                const videoData = JSON.parse(videoDataString);
                displayVideoResults(videoData);
            } catch (e) {
                console.error("Error parsing video data from localStorage", e);
                const resultsDiv = document.getElementById('results');
                if(resultsDiv) resultsDiv.innerHTML = '<p>Error displaying video data. Please try again.</p>';
            }
        } else {
            const resultsDiv = document.getElementById('results');
            if(resultsDiv) resultsDiv.innerHTML = '<p>No video data found. Please go back and submit a URL.</p>';
        }
    }
});

function displayVideoResults(data) {
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

            // **MODIFIED PART: Add audio information more clearly**
            let audioInfo = "";
            if (!format.acodec || format.acodec === 'none') {
                audioInfo = " (Video Only, No Audio)";
            } else {
                audioInfo = ` (Audio: ${format.acodec})`;
            }
            // You could also show vcodec if desired: `(V: ${format.vcodec || 'N/A'}, A: ${format.acodec || 'N/A'})`
            // For this change, we focus on making "No Audio" prominent.

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
}
