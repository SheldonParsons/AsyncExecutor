-- File: update_json_pro.lua

-- KEYS[1]: 我们要操作的 Redis key
-- ARGV[1]: 一个包含所有更新内容的 JSON 字符串, e.g., '{"level": 100, "status": "online"}'

-- 1. 读取并解码 Redis 中已有的 JSON 对象
local existing_json_str = redis.call('GET', KEYS[1])
if not existing_json_str then
  return nil
end

local success, main_obj = pcall(cjson.decode, existing_json_str)
if not success then
  return redis.error_reply("Value at key '" .. KEYS[1] .. "' is not a valid JSON object.")
end

-- 2. 解码从参数传入的、包含更新内容的 JSON 字符串
local updates_json_str = ARGV[1]
local success, updates_obj = pcall(cjson.decode, updates_json_str)
if not success then
  return redis.error_reply("Argument is not a valid JSON object.")
end

-- 3. 遍历 updates_obj, 并更新 main_obj
-- pairs() 用于遍历一个 table 的所有 key-value 对
for field, value in pairs(updates_obj) do
  main_obj[field] = value
end

-- 4. 将更新后的 main_obj 重新编码并存回 Redis
local new_json_str = cjson.encode(main_obj)
redis.call('SET', KEYS[1], new_json_str)
redis.call('EXPIRE', KEYS[1], 3600)

-- 5. 返回新值
return new_json_str