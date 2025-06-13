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
                const response = await fetch('/api/download', {
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

                // Store data and redirect
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

    // Function to display messages on the page
    function displayMessage(message, type = 'info') {
        if (messageDiv) {
            messageDiv.textContent = message;
            messageDiv.className = `message ${type}`; // Use classes for styling
            messageDiv.style.display = 'block';
        } else {
            // Fallback if messageDiv is not on the current page (e.g. result.html)
            alert(message);
        }
    }

    // Logic for result.html (if this script is also linked there or a separate one is used)
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
            // Optional: Clear data from localStorage after use if not needed anymore
            // localStorage.removeItem('videoData');
        } else {
            const resultsDiv = document.getElementById('results');
            if(resultsDiv) resultsDiv.innerHTML = '<p>No video data found. Please go back and submit a URL.</p>';
        }
    }
});

function displayVideoResults(data) {
    const resultsDiv = document.getElementById('results');
    if (!resultsDiv) return;

    resultsDiv.innerHTML = ''; // Clear previous results

    if (data.error) {
        resultsDiv.innerHTML = `<p class="error">Error: ${data.error}</p>`;
        return;
    }

    const titleElement = document.createElement('h2');
    titleElement.textContent = data.title || 'Untitled Video';
    resultsDiv.appendChild(titleElement);

    if (data.thumbnail) {
        const thumbnailElement = document.createElement('img');
        thumbnailElement.src = data.thumbnail;
        thumbnailElement.alt = 'Video Thumbnail';
        thumbnailElement.style.maxWidth = '300px'; // Basic styling
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

            let formatDescription = `${format.format_note || format.resolution || format.format_id} (${format.ext})`;
            if (format.filesize_approx) {
                formatDescription += ` - ${(format.filesize_approx / 1024 / 1024).toFixed(2)} MB`;
            }

            listItem.innerHTML = `
                <span>${formatDescription}</span>
                <div class="format-buttons">
                    <a href="${format.url}" target="_blank" download class="download-btn">Download</a>
                    <button class="copy-btn" data-url="${format.url}">Copy Link</button>
                </div>
            `;
            formatsList.appendChild(listItem);
        });
    } else {
        const noFormatsItem = document.createElement('li');
        noFormatsItem.textContent = 'No downloadable formats found for this video, or there was an issue fetching them.';
        formatsList.appendChild(noFormatsItem);
    }
    resultsDiv.appendChild(formatsList);

    // Add event listeners for copy buttons
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
