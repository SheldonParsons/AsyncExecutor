-- File: increment_json_fields.lua

-- KEYS[1]: 我们要操作的 Redis key
-- ARGV[1]: 一个包含自增字段和值的 JSON 字符串, e.g., '{"level": 2, "gold": 50}'

-- 1. 读取并解码 Redis 中已有的 JSON 对象
local existing_json_str = redis.call('GET', KEYS[1])
if not existing_json_str then
    return nil -- 如果 key 不存在，无法自增
end

local success, main_obj = pcall(cjson.decode, existing_json_str)
if not success then
    return redis.error_reply("Value at key '" .. KEYS[1] .. "' is not a valid JSON object.")
end

-- 2. 解码从参数传入的、包含自增内容的 JSON 字符串
local increments_json_str = ARGV[1]
local success, increments_obj = pcall(cjson.decode, increments_json_str)
if not success then
    return redis.error_reply("Argument is not a valid JSON object for increments.")
end

-- 3 & 4. 遍历需要自增的字段，并执行增加操作
for field, increment_value in pairs(increments_obj) do
    -- 安全检查：确保要增加的值本身是数字
    if type(increment_value) ~= "number" then
        return redis.error_reply("Increment value for field '" .. field .. "' is not a number.")
    end

    -- 获取当前字段的值。如果字段在原JSON中不存在，我们将其默认为 0
    local current_value = main_obj[field] or 0

    -- 安全检查：确保原有的值也是数字，才能进行数学运算
    if type(current_value) ~= "number" then
        return redis.error_reply("Existing value for field '" .. field .. "' is not a number and cannot be incremented.")
    end

    -- 执行自增
    main_obj[field] = current_value + increment_value
end

-- 5. 将更新后的 main_obj 重新编码并存回 Redis
local new_json_str = cjson.encode(main_obj)
redis.call('SET', KEYS[1], new_json_str)
redis.call('EXPIRE', KEYS[1], 3600)

-- 返回新值
return new_json_str
