@extends('layouts.app')

@section('content')
    <h2>Channels</h2>

    @if ($channels->isEmpty())
        <p>No channels found.</p>
    @else
        <ul class="channel-list">
            @foreach ($channels as $channel)
                <li>
                    <a href="{{ route('channels.show', $channel) }}">
                        {{ $channel->title }}
                        @if ($channel->username)
                            ({{ '@' . $channel->username }})
                        @endif
                    </a>
                </li>
            @endforeach
        </ul>
    @endif
@endsection

