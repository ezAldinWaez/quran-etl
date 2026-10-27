function Meta(meta)
  local includes = meta["header-includes"]
  if includes == nil or pandoc.utils.type(includes) ~= "List" then
    return meta
  end

  local blocks = pandoc.Blocks({})
  for _, item in ipairs(includes) do
    if pandoc.utils.type(item) ~= "Blocks" then
      return meta
    end
    blocks:extend(item)
  end
  meta["header-includes"] = pandoc.MetaBlocks(blocks)
  return meta
end
