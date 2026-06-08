# vol-cogs
Useful cogs made by volunteers

# Main cogs
## Imagechecker
This uses perceptual hashing to "see" image files uploaded and punish users if they match any disallowed images. This is most useful for fighting against prolific crypto/MrBeast/AndrewTate style spam. Quick Basic setup is:
1. `[!]repo add vol-cogs https://github.com/Flip-volunteers/vol-cogs`
2. `[!]cog install vol-cogs imagechecker`
3. `[!]load imagechecker`
4. `[!]setmodlogchannel somechannelIDhere` (set this to a channel for notifcations it muted/banned someone)
5. `[!]setpunish timeout 1d` this sets it to auto-apply a 1 day timeout for any users it detects attempting to share images

From there, you can use the `[!]addimages` command combined with uploading image files to have it scan attached files and add them to the detection list.
Only those with moderation or manage message permissions will be able to add/remove items to the detection system. 
