<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Telegram Channel Reader</title>
    <style>
        body {
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            margin: 0;
            padding: 0;
            background: #f5f5f5;
            color: #222;
        }
        header {
            background: #1f2937;
            color: #fff;
            padding: 1rem 2rem;
        }
        header h1 {
            margin: 0;
            font-size: 1.5rem;
        }
        main {
            padding: 1.5rem 2rem;
        }
        a {
            color: #2563eb;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        .channel-list li {
            margin-bottom: 0.5rem;
        }
        .message {
            background: #fff;
            border-radius: 4px;
            padding: 0.75rem 1rem;
            margin-bottom: 0.75rem;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        }
        .message time {
            font-size: 0.75rem;
            color: #6b7280;
        }
        .pagination {
            margin-top: 1rem;
        }
    </style>
</head>
<body>
    <header>
        <h1>Telegram Channel Reader</h1>
    </header>
    <main>
        @yield('content')
    </main>
</body>
</html>

