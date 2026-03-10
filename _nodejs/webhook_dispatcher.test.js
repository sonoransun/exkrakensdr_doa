const WebhookDispatcher = require('./webhook_dispatcher');

// Mock axios
jest.mock('axios', () => ({
    post: jest.fn(),
}));
const axios = require('axios');

describe('WebhookDispatcher', () => {
    let dispatcher;

    beforeEach(() => {
        dispatcher = new WebhookDispatcher();
        jest.clearAllMocks();
        jest.useFakeTimers();
    });

    afterEach(() => {
        jest.useRealTimers();
    });

    describe('updateConfig', () => {
        test('parses comma-separated URLs', () => {
            dispatcher.updateConfig({
                webhook_urls: 'http://a.com/hook, http://b.com/hook',
            });
            expect(dispatcher.urls).toEqual(['http://a.com/hook', 'http://b.com/hook']);
        });

        test('empty URLs string results in empty array', () => {
            dispatcher.updateConfig({ webhook_urls: '' });
            expect(dispatcher.urls).toEqual([]);
        });

        test('updates retry settings', () => {
            dispatcher.updateConfig({
                webhook_retry_count: 5,
                webhook_retry_delay_ms: 2000,
            });
            expect(dispatcher.retryCount).toBe(5);
            expect(dispatcher.retryDelayMs).toBe(2000);
        });

        test('updates event toggles', () => {
            dispatcher.updateConfig({
                webhook_evt_signal_appear: false,
                webhook_evt_doa_change: false,
            });
            expect(dispatcher.enabledEvents.signal_appear).toBe(false);
            expect(dispatcher.enabledEvents.doa_change).toBe(false);
            // Unchanged events stay true
            expect(dispatcher.enabledEvents.signal_disappear).toBe(true);
        });
    });

    describe('dispatchEvents', () => {
        test('filters disabled event types', async () => {
            dispatcher.urls = ['http://hook.test/endpoint'];
            dispatcher.enabledEvents.signal_appear = false;
            axios.post.mockResolvedValue({ status: 200 });

            await dispatcher.dispatchEvents([
                { event_type: 'signal_appear', vfo_index: 0 },
                { event_type: 'doa_change', vfo_index: 1 },
            ]);

            // Only doa_change should be dispatched
            expect(axios.post).toHaveBeenCalledTimes(1);
            expect(axios.post.mock.calls[0][1].event_type).toBe('doa_change');
        });

        test('dispatches to all configured URLs', async () => {
            dispatcher.urls = ['http://a.test/hook', 'http://b.test/hook'];
            axios.post.mockResolvedValue({ status: 200 });

            await dispatcher.dispatchEvents([
                { event_type: 'signal_appear', vfo_index: 0 },
            ]);

            expect(axios.post).toHaveBeenCalledTimes(2);
        });
    });

    describe('_sendWithRetry', () => {
        test('increments totalDispatched on success', async () => {
            axios.post.mockResolvedValue({ status: 200 });

            await dispatcher._sendWithRetry('http://hook.test', { event_type: 'signal_appear' }, 0);

            expect(dispatcher.stats.totalDispatched).toBe(1);
            expect(dispatcher.stats.lastEventTime).toBeTruthy();
        });

        test('retries on failure', async () => {
            const spy = jest.spyOn(global, 'setTimeout');
            axios.post.mockRejectedValue(new Error('Network error'));

            await dispatcher._sendWithRetry('http://hook.test', { event_type: 'signal_appear' }, 0);

            // Should have scheduled a retry via setTimeout
            expect(spy).toHaveBeenCalled();
            spy.mockRestore();
        });

        test('gives up after max retries', async () => {
            axios.post.mockRejectedValue(new Error('Network error'));
            dispatcher.retryCount = 0;

            await dispatcher._sendWithRetry('http://hook.test', { event_type: 'signal_appear' }, 0);

            // After retryCount=0 and attempt=0, should fail since attempt >= retryCount
            // Wait, the condition is attempt < this.retryCount. With retryCount=0 and attempt=0: 0 < 0 is false
            // So it should increment totalFailed
            expect(dispatcher.stats.totalFailed).toBe(1);
            expect(dispatcher.stats.lastError).toBe('Network error');
        });
    });

    describe('getStats', () => {
        test('returns URL count', () => {
            dispatcher.urls = ['http://a.test', 'http://b.test'];
            const stats = dispatcher.getStats();
            expect(stats.configuredUrls).toBe(2);
        });

        test('includes dispatch stats', () => {
            dispatcher.stats.totalDispatched = 10;
            dispatcher.stats.totalFailed = 2;
            const stats = dispatcher.getStats();
            expect(stats.totalDispatched).toBe(10);
            expect(stats.totalFailed).toBe(2);
        });
    });
});
