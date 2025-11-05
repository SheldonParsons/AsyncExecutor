-- File: update_list_json_element.lua

-- KEYS[1]: 我们要操作的 Redis List key。
-- ARGV[2]: 要修改的元素的下标 (index)。
-- ARGV[1]: 一个包含所有更新内容的 JSON 字符串, e.g., '{"level": 100, "status": "online"}'

-- 1. 从 ARGV 获取参数
local index = ARGV[2]
local updates_json_str = ARGV[1]

-- 2. 通过 LINDEX 读取列表中指定下标的元素 (它是一个 JSON 字符串)
local existing_json_str = redis.call('LINDEX', KEYS[1], index)

-- 如果 key 不存在或下标越界，LINDEX 会返回 nil
if not existing_json_str then
    return redis.error_reply("Index out of bounds or key does not exist for key '" .. KEYS[1] .. "'.")
end

-- 3. 解码从 Redis 读取的 JSON 和从参数传入的 JSON
local success, main_obj = pcall(cjson.decode, existing_json_str)
if not success then
    return redis.error_reply("The element at index " .. index .. " is not a valid JSON object.")
end

local success, updates_obj = pcall(cjson.decode, updates_json_str)
if not success then
    return redis.error_reply("Argument is not a valid JSON object for updates.")
end

-- 4. 遍历 updates_obj, 并更新 main_obj
for field, value in pairs(updates_obj) do
    if field == 'done_step_count' or field == 'failed_step_count' or field == 'skipped_step_count' then
        main_obj[field] = main_obj[field] + value
    else
        main_obj[field] = value
    end
end

-- 5. 将更新后的 main_obj 重新编码为 JSON 字符串
local new_json_str = cjson.encode(main_obj)

-- 6. 通过 LSET 将新的 JSON 字符串写回到原来的下标位置
redis.call('LSET', KEYS[1], index, new_json_str)

-- 7. 返回新值，方便客户端确认
return new_json_str
