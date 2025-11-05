-- ARGV[1]: the new value to be added (as a JSON string)
-- KEYS[1]: the name of the list key

-- 1. Get the last item from the list
local last_item_str = redis.call('LINDEX', KEYS[1], -1)

-- A flag to check if we updated the item
local updated = false

-- 2. Check if the list and the last item exist
if last_item_str then
    -- Use pcall (protected call) for safe JSON decoding
    local last_item_obj
    local success, result = pcall(cjson.decode, last_item_str)
    if success then
        last_item_obj = result
    end

    local new_item_obj
    success, result = pcall(cjson.decode, ARGV[1])
    if success then
        new_item_obj = result
    end

    -- 3. Perform the logical comparison
    if last_item_obj and new_item_obj and
        type(last_item_obj) == 'table' and last_item_obj['type'] == 'action_script_print' and
        last_item_obj['desc'] == new_item_obj['desc']
    then
        -- Conditions met: Increment 'times' and update the item
        last_item_obj['times'] = (last_item_obj['times'] or 0) + 1
        local modified_item_json = cjson.encode(last_item_obj)

        -- Use LSET to update the last item in place
        redis.call('LSET', KEYS[1], -1, modified_item_json)
        updated = true
    end
end

-- 4. If we didn't update, we must append
if not updated then
    -- Append the new item to the list
    redis.call('RPUSH', KEYS[1], ARGV[1])
    -- Set/update the expiration time
    redis.call('EXPIRE', KEYS[1], 604800)
end
