local results = {}
local ops = cjson.decode(ARGV[1])

for i, op in ipairs(ops) do
    if op[1] == 'GET' then
        local val = redis.call('GET', op[2])
        table.insert(results, val or false)

    elseif op[1] == 'LRANGE' then
        local items = redis.call('LRANGE', op[2], op[3], op[4])
        table.insert(results, items)

    elseif op[1] == 'RPUSH' then
        redis.call('RPUSH', op[2], op[3])
        redis.call('EXPIRE', op[2], 604800)
        table.insert(results, false)

    elseif op[1] == 'MRPUSH' then
        redis.call('RPUSH', op[2], unpack(op[3]))
        redis.call('EXPIRE', op[2], 604800)
        table.insert(results, false)

    elseif op[1] == 'SET' then
        redis.call('SET', op[2], op[3])
        redis.call('EXPIRE', op[2], 604800)
        table.insert(results, false)
    end
end

return cjson.encode(results)