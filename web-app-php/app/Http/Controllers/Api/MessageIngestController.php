<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Channel;
use App\Models\Message;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class MessageIngestController extends Controller
{
    public function store(Request $request)
    {
        // Simple API key check; in a real app, use something stronger.
        $apiKey = $request->header('X-API-Key');
        if ($apiKey !== config('services.ingest.api_key')) {
            return response()->json(['error' => 'Unauthorized'], 401);
        }

        $payload = $request->validate([
            'messages' => ['required', 'array'],
            'messages.*.telegram_channel_id' => ['required', 'integer'],
            'messages.*.channel_username' => ['nullable', 'string'],
            'messages.*.channel_title' => ['required', 'string'],
            'messages.*.message_id' => ['required', 'integer'],
            'messages.*.text' => ['nullable', 'string'],
            'messages.*.media_url' => ['nullable', 'string'],
            'messages.*.published_at' => ['required', 'date'],
        ]);

        $inserted = 0;
        $skipped = 0;

        DB::transaction(function () use ($payload, &$inserted, &$skipped) {
            foreach ($payload['messages'] as $item) {
                $channel = Channel::updateOrCreate(
                    ['telegram_id' => $item['telegram_channel_id']],
                    [
                        'username' => $item['channel_username'] ?? null,
                        'title' => $item['channel_title'],
                    ]
                );

                $message = Message::updateOrCreate(
                    [
                        'channel_id' => $channel->id,
                        'message_id' => $item['message_id'],
                    ],
                    [
                        'text' => $item['text'] ?? null,
                        'media_url' => $item['media_url'] ?? null,
                        'published_at' => $item['published_at'],
                        'synced_at' => now(),
                    ]
                );

                if ($message->wasRecentlyCreated) {
                    $inserted++;
                } else {
                    $skipped++;
                }
            }
        });

        return response()->json([
            'status' => 'ok',
            'inserted' => $inserted,
            'skipped' => $skipped,
        ]);
    }
}

