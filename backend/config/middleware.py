from django.contrib.auth import get_user_model


class AutoLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Ensure AuthenticationMiddleware has already run
        if hasattr(request, 'user') and not request.user.is_authenticated:
            User = get_user_model()
            user = User.objects.first()
            if user:
                request.user = user

        
        return self.get_response(request)
