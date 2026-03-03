<?php

namespace App\Http\Controllers;

use App\Models\Channel;
use Illuminate\Http\Request;

class ChannelController extends Controller
{
    public function index()
    {
        $channels = Channel::orderBy('title')->get();

        return view('channels.index', compact('channels'));
    }

    public function show(Channel $channel, Request $request)
    {
        $perPage = 50;

        $messages = $channel->messages()
            ->orderByDesc('published_at')
            ->paginate($perPage)
            ->withQueryString();

        return view('channels.show', compact('channel', 'messages'));
    }
}

