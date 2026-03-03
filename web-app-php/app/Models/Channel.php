<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Channel extends Model
{
    protected $table = 'channels';

    protected $fillable = [
        'telegram_id',
        'username',
        'title',
    ];

    public function messages(): HasMany
    {
        return $this->hasMany(Message::class);
    }
}

