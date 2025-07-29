const { WebClient } = require("@slack/web-api");

exports.handler = async (event) => {
    const { token, channel, ts, cursor } = JSON.parse(event.body || '{}');
    if (!token || !channel || !ts) {
        return { statusCode: 400, body: JSON.stringify({ error: "Thiếu token / channel / ts" }) };
    }

    try {
        const client = new WebClient(token);
        const response = await client.conversations.replies({
            retryConfig: {
                retries: 0  // 👈 tắt retry hoàn toàn
            },
            channel,
            ts,
            limit: 15,
            cursor: cursor || undefined,
        });

        return {
            statusCode: 200,
            body: JSON.stringify({
                messages: response.messages,
                next_cursor: response.response_metadata?.next_cursor || null
            }),
        };
    } catch (e) {
        return {
            statusCode: 500,
            body: JSON.stringify({ error: e.message }),
        };
    }
};
