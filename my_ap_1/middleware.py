from django.utils import timezone


class OnlineUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            profile = getattr(request.user, "profile", None)

            if profile:
                profile.is_online = True
                profile.last_seen = timezone.now()
                profile.save(update_fields=["is_online", "last_seen"])

        response = self.get_response(request)
        return response