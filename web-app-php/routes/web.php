<?php

use App\Http\Controllers\ChannelController;
use Illuminate\Support\Facades\Route;

Route::get('/', [ChannelController::class, 'index'])->name('channels.index');
Route::get('/channels/{channel}', [ChannelController::class, 'show'])->name('channels.show');

