task.wait(1)

local HttpService = game:GetService("HttpService")
print("고번 시스템 작동 시작!")
game.Players.PlayerAdded:Connect(function(player)
	print("인식 받음")
	-- API에서 유저 정보 받아오기
	local response = HttpService:GetAsync("주소:포트/api/users/" .. player.Name)
	local userData = HttpService:JSONDecode(response)

	-- 유저 정보가 있을 경우
	if userData.id and userData.discord then
		print("데이터 받음")
		-- BillboardGui 생성
		local billboard = game.ReplicatedStorage.BillboardGui:Clone()
		billboard.Parent = player.Character.Head
		--설정
		billboard.name.Text = player.Name
		billboard.name.num.Text = userData.id
		print("Successful")
	else
		-- 유저가 등록되지 않았다면 퇴장 처리
		player:Kick("고유번호가 등록되지 않았습니다. 관리자에게 문의하세요.")
	end
end)
