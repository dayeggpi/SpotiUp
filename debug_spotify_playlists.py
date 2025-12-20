#!/usr/bin/env python3
"""
Simple debug script to list all playlists and identify Spotify-created ones.
This helps debug why Spotify-created playlists might not be showing in backups.
"""

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from config import (
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    SPOTIFY_REDIRECT_URI,
    SPOTIFY_SCOPES
)

def main():
    print("🔍 Debugging Spotify Playlists\n")
    print("=" * 80)

    # Authenticate
    print("\n📝 Authenticating with Spotify...")
    auth_manager = SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=' '.join(SPOTIFY_SCOPES),
        open_browser=True
    )

    sp = spotipy.Spotify(auth_manager=auth_manager)

    # Get current user info
    user_info = sp.current_user()
    user_id = user_info['id']
    print(f"✅ Authenticated as: {user_info.get('display_name', user_id)}")
    print(f"   User ID: {user_id}")
    print("\n" + "=" * 80)

    # Fetch all playlists
    print("\n📚 Fetching all playlists...\n")

    all_playlists = []
    spotify_created = []
    user_created = []
    collaborative = []
    followed = []

    offset = 0
    limit = 50

    while True:
        results = sp.current_user_playlists(limit=limit, offset=offset)

        if not results or not results.get('items'):
            break

        for item in results['items']:
            if item is None:
                continue

            playlist_id = item.get('id')
            playlist_name = item.get('name', 'Unknown')
            owner = item.get('owner', {})
            owner_id = owner.get('id', '')
            owner_name = owner.get('display_name', owner_id)
            is_collab = item.get('collaborative', False)
            track_count = item.get('tracks', {}).get('total', 0)

            playlist_info = {
                'id': playlist_id,
                'name': playlist_name,
                'owner_id': owner_id,
                'owner_name': owner_name,
                'is_collaborative': is_collab,
                'track_count': track_count
            }

            all_playlists.append(playlist_info)

            # Categorize
            if owner_id.lower() == 'spotify':
                spotify_created.append(playlist_info)
            elif owner_id == user_id:
                user_created.append(playlist_info)
            else:
                followed.append(playlist_info)

            if is_collab:
                collaborative.append(playlist_info)

        if results.get('next') is None:
            break

        offset += limit

    # Print summary
    print("\n📊 SUMMARY")
    print("=" * 80)
    print(f"Total playlists in your library: {len(all_playlists)}")
    print(f"  ├─ Created by YOU: {len(user_created)}")
    print(f"  ├─ Created by SPOTIFY: {len(spotify_created)}")
    print(f"  ├─ Followed (other users): {len(followed)}")
    print(f"  └─ Collaborative: {len(collaborative)}")

    # List Spotify-created playlists
    if spotify_created:
        print("\n" + "=" * 80)
        print(f"\n🎵 SPOTIFY-CREATED PLAYLISTS ({len(spotify_created)} found)")
        print("=" * 80)
        print("\nThese are playlists created by Spotify but saved to your library:")
        print("(e.g., Discover Weekly, Release Radar, Daily Mixes, etc.)\n")

        for i, pl in enumerate(spotify_created, 1):
            print(f"{i:3d}. {pl['name']}")
            print(f"      ID: {pl['id']}")
            print(f"      Owner: {pl['owner_name']} (ID: {pl['owner_id']})")
            print(f"      Tracks: {pl['track_count']}")
            print()
    else:
        print("\n⚠️  NO Spotify-created playlists found in your library!")
        print("    This could mean:")
        print("    - You haven't saved any Spotify playlists")
        print("    - Or there might be an issue with how we're detecting them")

    # List all playlists for reference
    print("\n" + "=" * 80)
    print(f"\n📋 ALL PLAYLISTS IN YOUR LIBRARY")
    print("=" * 80)
    print(f"{'#':<4} {'Owner':<20} {'Type':<15} {'Name':<40} {'Tracks':<8}")
    print("-" * 90)

    for i, pl in enumerate(all_playlists, 1):
        # Determine type
        if pl['owner_id'].lower() == 'spotify':
            pl_type = "SPOTIFY"
        elif pl['owner_id'] == user_id:
            pl_type = "YOU"
        else:
            pl_type = "FOLLOWED"

        if pl['is_collaborative']:
            pl_type += " (collab)"

        # Truncate name if too long
        name = pl['name'][:37] + "..." if len(pl['name']) > 40 else pl['name']
        owner = pl['owner_name'][:17] + "..." if len(pl['owner_name']) > 20 else pl['owner_name']

        print(f"{i:<4} {owner:<20} {pl_type:<15} {name:<40} {pl['track_count']:<8}")

    print("\n" + "=" * 80)
    print("\n✅ Debug complete!")
    print("\nIf you see Spotify-created playlists above but they're not in your backup,")
    print("check your backup settings and make sure 'include_spotify_playlists' is True.")

if __name__ == "__main__":
    main()
