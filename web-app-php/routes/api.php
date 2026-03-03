<?php

use App\Http\Controllers\Api\MessageIngestController;
use Illuminate\Support\Facades\Route;

Route::post('/messages', [MessageIngestController::class, 'store']);

