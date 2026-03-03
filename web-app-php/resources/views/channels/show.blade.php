@extends('layouts.app')

@section('content')
    <p><a href="{{ route('channels.index') }}">&larr; Back to channels</a></p>

    <h2>{{ $channel->title }}</h2>
    @if ($channel->username)
        <p>{{ '@' . $channel->username }}</p>
    @endif

    @forelse ($messages as $message)
        <article class="message">
            <time datetime="{{ $message->published_at->toIso8601String() }}">
                {{ $message->published_at->format('Y-m-d H:i:s') }}
            </time>
            <div>
                {!! nl2br(e($message->text)) !!}
            </div>
            @if ($message->media_url)
                <div>
                    <a href="{{ $message->media_url }}" target="_blank" rel="noopener noreferrer">
                        View media
                    </a>
                </div>
            @endif
        </article>
    @empty
        <p>No messages in the last 48 hours.</p>
    @endforelse

    <div class="pagination">
        {{ $messages->links() }}
    </div>
@endsection

