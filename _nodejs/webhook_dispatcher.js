const axios = require('axios');

class WebhookDispatcher {
    constructor() {
        this.urls = [];
        this.retryCount = 3;
        this.retryDelayMs = 1000;
        this.enabledEvents = {
            signal_appear: true,
            signal_disappear: true,
            novel_frequency: true,
            doa_change: true,
            power_alert: true,
        };
        this.stats = {
            totalDispatched: 0,
            totalFailed: 0,
            lastEventTime: null,
            lastError: null,
        };
    }

    /**
     * Parse webhook-related fields from a settings object (settings.json format)
     * and apply them to this dispatcher instance.
     */
    updateConfig(settings) {
        if (settings.webhook_urls !== undefined) {
            this.urls = String(settings.webhook_urls)
                .split(',')
                .map(u => u.trim())
                .filter(u => u.length > 0);
        }

        if (settings.webhook_retry_count !== undefined) {
            this.retryCount = Number(settings.webhook_retry_count);
        }

        if (settings.webhook_retry_delay_ms !== undefined) {
            this.retryDelayMs = Number(settings.webhook_retry_delay_ms);
        }

        const eventMap = {
            webhook_evt_signal_appear: 'signal_appear',
            webhook_evt_signal_disappear: 'signal_disappear',
            webhook_evt_novel_freq: 'novel_frequency',
            webhook_evt_doa_change: 'doa_change',
            webhook_evt_power_alert: 'power_alert',
        };

        for (const [settingsKey, eventType] of Object.entries(eventMap)) {
            if (settings[settingsKey] !== undefined) {
                this.enabledEvents[eventType] = Boolean(settings[settingsKey]);
            }
        }
    }

    /**
     * Dispatch an array of events to all configured webhook URLs.
     * Each event object must have an `event_type` property.
     * Dispatches are fire-and-forget -- this method does not await retries.
     */
    async dispatchEvents(events) {
        for (const event of events) {
            if (!this.enabledEvents[event.event_type]) {
                continue;
            }

            for (const url of this.urls) {
                // Fire-and-forget: intentionally not awaited
                this._sendWithRetry(url, event, 0);
            }
        }
    }

    /**
     * POST the event as JSON to the given URL, retrying with exponential
     * backoff on failure.
     */
    async _sendWithRetry(url, event, attempt = 0) {
        try {
            await axios.post(url, event, {
                timeout: 5000,
                headers: { 'Content-Type': 'application/json' },
            });

            this.stats.totalDispatched++;
            this.stats.lastEventTime = new Date().toISOString();
        } catch (err) {
            if (attempt < this.retryCount) {
                const delay = this.retryDelayMs * Math.pow(2, attempt);
                setTimeout(() => {
                    this._sendWithRetry(url, event, attempt + 1);
                }, delay);
            } else {
                this.stats.totalFailed++;
                this.stats.lastError = err.message || String(err);
                console.error(
                    `[WebhookDispatcher] Failed to deliver event to ${url} after ${this.retryCount + 1} attempts: ${this.stats.lastError}`
                );
            }
        }
    }

    /**
     * Return a snapshot of dispatch statistics plus the number of
     * currently configured webhook URLs.
     */
    getStats() {
        return {
            ...this.stats,
            configuredUrls: this.urls.length,
        };
    }
}

module.exports = WebhookDispatcher;
