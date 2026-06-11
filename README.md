# vol-cogs
Useful cogs made by Flip-volunteers group.

# Main cogs
## Imagechecker
This uses [perceptual hashing](https://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html) to "see" image files uploaded and punish users if they match any disallowed images. This is most useful for fighting against prolific crypto/MrBeast/AndrewTate style spam. Quick Basic setup is:
1. `[p]repo add vol-cogs https://github.com/Flip-volunteers/vol-cogs`
2. `[p]cog install vol-cogs imagechecker`
3. `[p]load imagechecker`
4. `[p]imgcheckcmds setmodlogchannel somechannelIDhere` (set this to a channel for notifcations it muted/banned someone)
5. `[p]imgcheckcmds setpunish timeout 1d` this sets it to auto-apply a 1 day timeout for any users it detects attempting to share images

From there, you can use the `[p]addimages` command combined with uploading image files to have it scan attached files and add them to the detection list.
Only those with moderation or manage message permissions will be able to add/remove items to the detection system. 

see `[p]help imgcheckcmds` for configuration options and other potentially useful commands.

## MessageMover
This is a simple Message Mover cog for red that allows moderators and anyone with a set role to "move" messages to another channel they have access to via a right click context menu action. 
To do this, Redbot will need access to the ability to manage/remove webhooks in order to synthetically "clone" a user's message to another channel. 

Quick and basic setup:
1. `[p]repo add vol-cogs https://github.com/Flip-volunteers/vol-cogs`
2. `[p]cog install vol-cogs MessageMover`
3. `[p]load MessageMover`
4. `[p]slash enablecog MessageMover`
5. `[p]slash sync`
6. `[p]moveset addrole RoleIDHere` swapping RoleIDHere with whatever discord role should be able to move messages. 

After about a minute or so, the new setting should be visible when you right click a message, under the "apps" section of the context menu. 
